"""BFF 基座 — 等同 Nuxt 的 server/api 层

提供 HTTP 客户端 + 模板渲染 + Token 传递的通用基础设施。
用户继承 BFFBase，只需写业务方法。

v0.5.0 改进：
- 干掉 clone 模式：用 contextvars 传递认证信息，BFF 方法直接用 self.auth_token / self.current_user_id
- 共享 httpx 客户端：所有 BFF 实例共享一个连接池（不再每类各持一个）
- 修复 _delete() 缺少 import json 的 Bug
- 删除死代码：with_auth()、with_user()、template_dirs 废弃参数、close() 兼容方法

v0.4.0 改进：
- 路由自注册：BFF 方法加 @get/@post/@put/@delete 装饰器 → register() 自动注册
- 认证自动注入：装饰器声明 auth 级别（none/token/optional/required）

使用方式：
    from pynuxt.bff import BFFBase, get, post

    class FeedBFF(BFFBase):
        prefix = "/bff/posts"

        @get("/", auth="optional")
        async def get_posts(self, feed: str = Query("global")):
            posts = await self._get("/api/posts", params={"feed": feed})
            return self._render("components/post_list.html", data=posts)

    # 一行注册：
    FeedBFF.register(app, "http://localhost:8012")
"""

import inspect
import json
from inspect import Parameter

import httpx
from fastapi import APIRouter, Depends
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


# ==================== Handler 构建 ====================

def _build_handler(instance, method, meta: _RouteMeta):
    """构建 FastAPI 路由 handler：自动注入认证依赖，设置请求级上下文

    核心机制：
    1. 从 BFF 方法签名复制参数（去掉 self）
    2. 根据 auth 级别追加认证依赖（Depends）
    3. handler 运行时设置 contextvars（替代旧版 clone 模式）
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

        # 设置请求级上下文（替代 clone，BFF 方法通过属性读取）
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
    """BFF 基座 — HTTP 客户端 + 模板渲染 + Token 传递 + 路由自注册

    子类只需实现业务方法，用 @get/@post 装饰器声明路由。
    认证信息通过 contextvars 自动传递，无需手动 with_auth().with_user()。
    """

    prefix = ""  # 子类覆盖，如 "/bff/posts"

    # 类级共享 httpx 客户端（所有 BFF 实例共享一个连接池）
    _shared_client: httpx.AsyncClient | None = None
    _api_base: str = ""

    def __init__(self, api_base: str = None):
        """初始化 BFF 基座

        Args:
            api_base: 后端 API 地址（首次设置后类级共享）
        """
        if api_base:
            BFFBase._api_base = api_base.rstrip("/")

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
        """扫描 @route 装饰的方法，自动注册为 FastAPI 路由

        用法：
            FeedBFF.register(app, "http://localhost:8012")

        Returns:
            BFF 实例（兼容旧代码，实际不再需要追踪）
        """
        instance = cls(api_base)
        router = APIRouter(prefix=cls.prefix)

        # 扫描所有带 _bff_route 标记的方法
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

        app.include_router(router)
        return instance

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
