"""BFF 基座 — 等同 Nuxt 的 server/api 层

提供 HTTP 客户端 + 模板渲染 + Token 传递的通用基础设施。
用户继承 BFFBase，只需写业务方法。

核心机制：
- 路由自注册：BFF 方法加 @get/@post/@put/@delete 装饰器 → register() 自动注册
- 认证自动注入：装饰器声明 auth 级别（none/token/optional/required）
- contextvars 传递认证：请求级隔离，无需克隆实例
- 共享 httpx 客户端：所有 BFF 子类共享一个连接池
- CrudAction 声明式路由：常见 CRUD 模式 3 行搞定

使用方式：
    from pynuxt.bff import BFFBase, get, post, CrudAction

    # 方式一：装饰器（复杂逻辑）
    class FeedBFF(BFFBase):
        prefix = "/bff/posts"

        @get("", auth="optional")
        async def get_posts(self, feed: str = Query("global")):
            posts = await self._get("/api/posts", params={"feed": feed})
            return self._render("components/post_list.html", data=posts)

    # 方式二：CrudAction（标准 CRUD）
    class FriendBFF(BFFBase):
        prefix = "/bff/friends"

        list = CrudAction(backend="/api/friends/requests",
                          template="components/friend_request_list.html", auth="token")
        send = CrudAction(backend="/api/friends/requests/{username}", method="POST",
                          template="components/friend_button.html", auth="token",
                          template_context={"status": "pending"})
        respond = CrudAction(backend="/api/friends/requests/{request_id}", method="PUT",
                             refresh="list", auth="token")

    # 一行注册：
    FeedBFF.register(app, "http://localhost:8000")
"""

import inspect
import json
import re
from inspect import Parameter

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from pynuxt.context import _request_token, _request_user_id
from pynuxt.templates import env
from pynuxt.errors import BFFError


# ==================== 路由装饰器 ====================

class _RouteMeta:
    """路由元数据（由装饰器挂载到方法上）"""

    def __init__(self, method: str, path: str, auth: str, response_class, kwargs: dict):
        self.method = method.upper()
        self.path = path
        self.auth = auth  # "none" | "token" | "optional" | "required"
        self.response_class = response_class
        self.kwargs = kwargs


def route(method: str, path: str, auth: str = "optional",
          response_class=HTMLResponse, **kwargs):
    """装饰器：标记 BFF 方法为路由端点

    Args:
        method: HTTP 方法（GET/POST/PUT/DELETE）
        path: 路由路径（相对于 prefix）
        auth: 认证级别
            - "none": 无认证
            - "token": 仅注入 Token（可选，str|None）
            - "optional": Token + 可选 user_id（用于模板渲染）
            - "required": Token + 必须 user_id（未登录 401）
        response_class: FastAPI 响应类（默认 HTMLResponse）
    """
    def decorator(func):
        func._bff_route = _RouteMeta(method, path, auth, response_class, kwargs)
        return func
    return decorator


def get(path: str, **kwargs):
    """快捷装饰器：GET 路由"""
    return route("GET", path, **kwargs)


def post(path: str, **kwargs):
    """快捷装饰器：POST 路由"""
    return route("POST", path, **kwargs)


def put(path: str, **kwargs):
    """快捷装饰器：PUT 路由"""
    return route("PUT", path, **kwargs)


def delete(path: str, **kwargs):
    """快捷装饰器：DELETE 路由"""
    return route("DELETE", path, **kwargs)


# ==================== CrudAction 声明式路由 ====================

class CrudAction:
    """声明式 BFF 动作 — 标准 CRUD 模式 3 行搞定

    大多数 BFF 方法都是"调后端 API → 渲染模板"的固定模式。
    CrudAction 把这个模式声明化，省去手写 handler 的重复代码。

    两种渲染模式（互斥）：
    - template: 调后端 → 用返回数据渲染模板
    - refresh: 调后端 → 重新执行另一个 action 的逻辑

    Args:
        backend: 后端 API 路径，支持 {param} 占位符
        method: HTTP 方法（GET/POST/PUT/DELETE），默认 GET
        path: BFF 路由路径（相对于 prefix），默认 ""（即 prefix 本身）
        template: 渲染的 Jinja2 模板路径
        refresh: 创建/更新后刷新的 action 名（互斥 template）
        auth: 认证级别（none/token/optional/required），默认 optional
        template_context: 额外模板上下文（静态 KV），默认 {}

    用法：
        class FriendBFF(BFFBase):
            prefix = "/bff/friends"

            list = CrudAction(backend="/api/friends/requests",
                              template="components/friend_request_list.html", auth="token")
            send = CrudAction(backend="/api/friends/requests/{username}", method="POST",
                              template="components/friend_button.html", auth="token",
                              template_context={"status": "pending"})
            respond = CrudAction(backend="/api/friends/requests/{request_id}", method="PUT",
                                 refresh="list", auth="token")
    """

    def __init__(
        self,
        backend: str,
        method: str = "GET",
        path: str = "",
        template: str | None = None,
        refresh: str | None = None,
        auth: str = "optional",
        template_context: dict | None = None,
    ):
        if template and refresh:
            raise ValueError("CrudAction: template 和 refresh 互斥，只能选一个")
        self.backend = backend
        self.method = method.upper()
        self.path = path
        self.template = template
        self.refresh = refresh
        self.auth = auth
        self.template_context = template_context or {}


def _build_crud_handler(instance, cls, action: CrudAction, action_name: str):
    """为 CrudAction 构建 FastAPI 路由 handler

    自动生成：路径参数提取 → 后端调用 → 模板渲染/刷新
    """
    # 延迟导入避免循环依赖
    from pynuxt.auth import get_token, get_current_user_id, get_optional_user_id

    # 提取路径参数名（从 backend URL 和 BFF path 中）
    all_param_names = list(dict.fromkeys(
        re.findall(r'\{(\w+)\}', action.backend) +
        re.findall(r'\{(\w+)\}', action.path)
    ))

    # 构建签名：路径参数 + Request + 认证依赖
    params = []
    for pname in all_param_names:
        # 约定：以 _id 结尾的路径参数为 int，其余为 str
        annotation = int if pname.endswith("_id") else str
        params.append(Parameter(pname, Parameter.POSITIONAL_OR_KEYWORD, annotation=annotation))

    params.append(Parameter("request", Parameter.KEYWORD_ONLY, annotation=Request))

    # 认证依赖
    if action.auth in ("token", "optional", "required"):
        params.append(Parameter(
            "token", Parameter.KEYWORD_ONLY,
            default=Depends(get_token),
            annotation=str | None,
        ))
    if action.auth == "optional":
        params.append(Parameter(
            "user_id", Parameter.KEYWORD_ONLY,
            default=Depends(get_optional_user_id),
            annotation=int | None,
        ))
    elif action.auth == "required":
        params.append(Parameter(
            "user_id", Parameter.KEYWORD_ONLY,
            default=Depends(get_current_user_id),
            annotation=int,
        ))

    async def handler(**kwargs):
        # 提取认证参数并设置上下文
        token = kwargs.pop("token", None)
        user_id = kwargs.pop("user_id", None)
        request = kwargs.pop("request", None)
        _request_token.set(token)
        _request_user_id.set(user_id)

        # 提取路径参数
        path_params = {k: v for k, v in kwargs.items() if k in all_param_names}

        # 格式化后端 URL
        backend_url = action.backend.format(**path_params)

        # 提取非路径参数
        extra = {k: v for k, v in kwargs.items() if k not in all_param_names}

        # 调用后端
        if action.method == "GET":
            query_params = dict(request.query_params) if request else {}
            result = await instance._get(backend_url, params=query_params)
        elif action.method == "POST":
            form_data = await request.form() if request else {}
            data = {k: v for k, v in form_data.items() if k not in path_params}
            result = await instance._post(backend_url, data)
        elif action.method == "PUT":
            form_data = await request.form() if request else {}
            data = {k: v for k, v in form_data.items() if k not in path_params}
            result = await instance._put(backend_url, data)
        elif action.method == "DELETE":
            result = await instance._delete(backend_url, data=extra or None)
        else:
            raise BFFError(f"CrudAction 不支持 HTTP 方法: {action.method}")

        # 渲染：template 模式 或 refresh 模式
        if action.refresh:
            refresh_action = getattr(cls, action.refresh)
            if not isinstance(refresh_action, CrudAction):
                raise BFFError(f"CrudAction refresh='{action.refresh}' 不是 CrudAction")
            query_params = dict(request.query_params) if request else {}
            refresh_result = await instance._get(refresh_action.backend, params=query_params)
            # 构建模板上下文
            context = {"current_user_id": instance.current_user_id, "data": refresh_result}
            if isinstance(refresh_result, dict):
                context.update(refresh_result)
            context.update(refresh_action.template_context)
            return instance._render(refresh_action.template, **context)
        else:
            # 构建模板上下文：data 保留 + dict 展开 + 路径参数 + 静态上下文 + current_user_id
            context = {"current_user_id": instance.current_user_id, "data": result}
            # 后端返回 dict 时，同时展开到顶层（兼容 {{ status }} 和 {{ data.status }} 两种模板写法）
            if isinstance(result, dict):
                context.update(result)
            # 路径参数也传入模板（如 username）
            context.update(path_params)
            # 静态上下文最后覆盖（优先级最高）
            context.update(action.template_context)
            return instance._render(action.template, **context)

    handler.__signature__ = inspect.Signature(parameters=params)
    handler.__name__ = action_name
    handler.__doc__ = f"CrudAction: {action.method} {action.backend} → {action.template or f'refresh:{action.refresh}'}"

    return handler


# ==================== Handler 构建 ====================

def _build_handler(instance, method, meta: _RouteMeta):
    """构建 FastAPI 路由 handler：自动注入认证依赖，设置请求级上下文

    核心机制：
    1. 从 BFF 方法签名复制参数（去掉 self）
    2. 根据 auth 级别追加认证依赖（Depends）
    3. handler 运行时通过 contextvars 设置请求级认证上下文
    """
    # 原始签名去掉 self
    orig_sig = inspect.signature(method)
    params = [p for p in orig_sig.parameters.values() if p.name != "self"]

    # 延迟导入避免循环依赖
    from pynuxt.auth import get_token, get_current_user_id, get_optional_user_id

    # 根据 auth 级别注入依赖
    if meta.auth in ("token", "optional", "required"):
        params.append(Parameter(
            "token", Parameter.KEYWORD_ONLY,
            default=Depends(get_token),
            annotation=str | None,
        ))
    if meta.auth == "optional":
        params.append(Parameter(
            "user_id", Parameter.KEYWORD_ONLY,
            default=Depends(get_optional_user_id),
            annotation=int | None,
        ))
    elif meta.auth == "required":
        params.append(Parameter(
            "user_id", Parameter.KEYWORD_ONLY,
            default=Depends(get_current_user_id),
            annotation=int,
        ))

    async def handler(**kwargs):
        # 提取自动注入的认证参数
        token = kwargs.pop("token", None)
        user_id = kwargs.pop("user_id", None)

        # 设置请求级上下文（BFF 方法通过 self.auth_token / self.current_user_id 读取）
        _request_token.set(token)
        _request_user_id.set(user_id)

        return await method(instance, **kwargs)

    # 设置签名供 FastAPI 解析参数
    handler.__signature__ = orig_sig.replace(parameters=params)
    handler.__name__ = method.__name__
    handler.__doc__ = method.__doc__

    return handler


# ==================== BFFBase 基座 ====================

class BFFBase:
    """BFF 基座 — HTTP 客户端 + 模板渲染 + 认证传递 + 路由自注册

    子类只需实现业务方法，用 @get/@post 装饰器声明路由。
    认证信息通过 contextvars 自动传递，每个请求隔离，无需克隆实例。
    """

    prefix = ""  # 子类覆盖，如 "/bff/posts"

    # 类级共享 httpx 客户端（所有 BFF 子类共享一个连接池）
    _shared_client: httpx.AsyncClient | None = None
    _api_base: str = ""

    @classmethod
    def _get_client(cls) -> httpx.AsyncClient:
        """获取共享 httpx 客户端（懒初始化）"""
        if cls._shared_client is None or cls._shared_client.is_closed:
            cls._shared_client = httpx.AsyncClient(
                base_url=cls._api_base,
                timeout=10.0,
            )
        return cls._shared_client

    @classmethod
    async def close_all(cls):
        """关闭共享 httpx 客户端（应在应用退出时调用）"""
        if cls._shared_client and not cls._shared_client.is_closed:
            await cls._shared_client.aclose()
            cls._shared_client = None

    # ==================== 认证上下文（contextvars → 属性）====================

    @property
    def auth_token(self) -> str | None:
        """当前请求的认证 Token（从 contextvars 读取）"""
        return _request_token.get()

    @property
    def current_user_id(self) -> int | None:
        """当前请求的用户 ID（从 contextvars 读取）"""
        return _request_user_id.get()

    # ==================== 路由注册 ====================

    @classmethod
    def register(cls, app, api_base: str):
        """扫描 @route 装饰的方法和 CrudAction 属性，自动注册为 FastAPI 路由

        用法：
            FeedBFF.register(app, "http://localhost:8000")
        """
        BFFBase._api_base = api_base.rstrip("/")
        instance = cls()
        router = APIRouter(prefix=cls.prefix)

        # 扫描所有带 _bff_route 标记的方法（装饰器模式）
        for name in dir(cls):
            orig = getattr(cls, name)
            meta = getattr(orig, "_bff_route", None)
            if not meta:
                continue

            handler = _build_handler(instance, orig, meta)
            router.add_api_route(
                meta.path,
                handler,
                methods=[meta.method],
                response_class=meta.response_class,
                name=name,
                **meta.kwargs,
            )

        # 扫描 CrudAction 属性（声明式模式）
        for name in dir(cls):
            attr = getattr(cls, name)
            if not isinstance(attr, CrudAction):
                continue

            handler = _build_crud_handler(instance, cls, attr, name)
            router.add_api_route(
                attr.path,
                handler,
                methods=[attr.method],
                response_class=HTMLResponse,
                name=name,
            )

        app.include_router(router)

    # ==================== HTTP 辅助 ====================

    def _get_headers(self) -> dict:
        """获取通用 Headers（包含 Authorization Token）"""
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    # ==================== 框架层 ====================

    def _render(self, template_name: str, **kwargs) -> str:
        """渲染 Jinja2 模板"""
        tmpl = env.get_template(template_name)
        return tmpl.render(**kwargs)

    async def _get(self, path: str, params: dict = None) -> dict | list:
        """GET 请求后端 API"""
        try:
            response = await self._get_client().get(
                path, params=params, headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise BFFError(
                f"后端 GET {path} 失败: HTTP {e.response.status_code} - {e.response.text[:200]}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise BFFError(f"后端 GET {path} 网络错误: {e}", status_code=502) from e

    async def _post(self, path: str, data: dict) -> dict:
        """POST 请求后端 API（JSON 格式）"""
        try:
            response = await self._get_client().post(
                path, json=data, headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise BFFError(
                f"后端 POST {path} 失败: HTTP {e.response.status_code} - {e.response.text[:200]}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise BFFError(f"后端 POST {path} 网络错误: {e}", status_code=502) from e

    async def _post_form(self, path: str, data: dict) -> dict:
        """POST 请求后端 API（form-encoded 格式）

        适用于 HTMX 表单提交场景（后端用 Form(...) 接收）。
        """
        try:
            response = await self._get_client().post(
                path, data=data, headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise BFFError(
                f"后端 POST(form) {path} 失败: HTTP {e.response.status_code} - {e.response.text[:200]}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise BFFError(f"后端 POST(form) {path} 网络错误: {e}", status_code=502) from e

    async def _put(self, path: str, data: dict = None) -> dict:
        """PUT 请求后端 API（JSON 格式）"""
        try:
            response = await self._get_client().put(
                path, json=data, headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise BFFError(
                f"后端 PUT {path} 失败: HTTP {e.response.status_code} - {e.response.text[:200]}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise BFFError(f"后端 PUT {path} 网络错误: {e}", status_code=502) from e

    async def _put_form(self, path: str, data: dict = None) -> dict:
        """PUT 请求后端 API（form-encoded 格式）"""
        try:
            response = await self._get_client().put(
                path, data=data, headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise BFFError(
                f"后端 PUT(form) {path} 失败: HTTP {e.response.status_code} - {e.response.text[:200]}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise BFFError(f"后端 PUT(form) {path} 网络错误: {e}", status_code=502) from e

    async def _delete(self, path: str, data: dict = None) -> dict:
        """DELETE 请求后端 API（支持可选 body）"""
        kwargs = {"headers": self._get_headers()}
        if data:
            kwargs["content"] = json.dumps(data).encode()
            kwargs["headers"]["Content-Type"] = "application/json"
        try:
            response = await self._get_client().request("DELETE", path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise BFFError(
                f"后端 DELETE {path} 失败: HTTP {e.response.status_code} - {e.response.text[:200]}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise BFFError(f"后端 DELETE {path} 网络错误: {e}", status_code=502) from e
