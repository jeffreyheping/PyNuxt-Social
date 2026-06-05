"""文件系统路由引擎 — 等同 Nuxt 的 pages/ 自动路由

启动时扫描 pages/ 目录，为每个 .html 文件注册一条精确 GET 路由。
不再使用 catch-all 通配符，避免与 BFF 路由冲突。

映射规则：
  pages/index.html                     → GET /
  pages/about.html                     → GET /about
  pages/users/list.html                → GET /users/list
  pages/posts/[id].html                → GET /posts/{id}
  pages/users/[username]/index.html   → GET /users/{username}
  pages/users/[username]/followers.html → GET /users/{username}/followers

v0.5.1 改进：
- 启动时扫描注册精确路由，消除 catch-all 与 BFF 路由冲突
- 使用 env.get_template() 走模板缓存，替代 from_string()

使用方式：
  from pynuxt.routing import install_file_routing
  install_file_routing(app, env, pages_dir="pages", context_vars=my_async_fn)
"""

import asyncio
import inspect
import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from pynuxt.errors import render_error_html

logger = logging.getLogger(__name__)


def install_file_routing(
    app: FastAPI,
    env,
    pages_dir: str = "pages",
    context_vars=None,
    debug: bool = False,
):
    """扫描 pages/ 目录，为每个页面注册精确 GET 路由

    启动时一次性扫描，每个 .html 文件生成一条精确路由。
    路由与 BFF 路由平级，FastAPI 按优先级匹配，永远不会冲突。

    Args:
        app: FastAPI 实例
        env: Jinja2 Environment 实例（支持 _LazyEnv）
        pages_dir: 页面模板目录（相对于工作目录，通常为 "pages"）
        context_vars: 模板渲染时的额外上下文变量
            - dict: 静态变量，每次渲染都注入
            - callable(同步): 接收 request，返回 dict
            - callable(异步): 接收 request，返回 awaitable dict
        debug: 是否开启调试模式
    """
    routes = _scan_pages(pages_dir)

    for route_path, template_path, param_names in routes:
        _register_page_route(
            app, env, route_path, template_path,
            param_names, context_vars, debug,
        )
        params_info = f" [{', '.join(param_names)}]" if param_names else ""
        logger.info(f"  GET {route_path}{params_info} -> {template_path}")

    logger.info(f"已注册 {len(routes)} 条页面路由")


def _scan_pages(pages_dir: str) -> list:
    """扫描 pages/ 目录，返回路由定义列表

    Returns:
        [(route_path, template_path, param_names), ...]
        - route_path: FastAPI 路由路径，如 "/users/{username}"
        - template_path: 模板相对路径（相对于工作目录），如 "pages/users/[username]/index.html"
        - param_names: 动态参数名列表，如 ["username"]
    """
    routes = []

    for dirpath, dirnames, filenames in os.walk(pages_dir):
        for filename in sorted(filenames):
            if not filename.endswith(".html"):
                continue

            # 模板文件的相对路径（相对于工作目录，供 get_template 使用）
            full_path = os.path.join(dirpath, filename)
            template_path = os.path.relpath(full_path, ".").replace("\\", "/")

            # 文件路径 → 路由路径
            rel_parts = os.path.relpath(full_path, pages_dir)
            parts = rel_parts.replace(".html", "").split(os.sep)

            # 提取动态参数 [param] → {param}
            param_names = []
            route_parts = []
            for part in parts:
                if part.startswith("[") and part.endswith("]"):
                    param_name = part[1:-1]
                    param_names.append(param_name)
                    route_parts.append(f"{{{param_name}}}")
                else:
                    route_parts.append(part)

            # index → 目录根
            if route_parts and route_parts[-1] == "index":
                route_parts.pop()

            # 构建路由路径
            route_path = "/" + "/".join(route_parts) if route_parts else "/"

            routes.append((route_path, template_path, param_names))

    return routes


def _register_page_route(app, env, route_path, template_path, param_names,
                         context_vars, debug):
    """为单个页面注册精确 GET 路由（手动构建签名，避免 **kwargs 被 FastAPI 误解析）"""
    from inspect import Parameter

    # 构建正确的函数签名
    sig_params = [
        Parameter("request", Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
    ]
    for name in param_names:
        sig_params.append(Parameter(name, Parameter.KEYWORD_ONLY, annotation=str))

    async def handler(request: Request, **path_params):
        """页面渲染 handler"""
        # 构建模板上下文
        context = {
            "request": request,
            "title": f"PyNuxt - {route_path}",
            **path_params,
        }

        # 注入额外上下文（支持 async callable）
        if context_vars is not None:
            if callable(context_vars):
                result = context_vars(request)
                if asyncio.iscoroutine(result):
                    result = await result
                context.update(result)
            elif isinstance(context_vars, dict):
                context.update(context_vars)

        # 使用模板缓存渲染（替代 from_string，利用 Jinja2 编译缓存）
        try:
            template = env.get_template(template_path)
            html = template.render(**context)
        except Exception as e:
            html = render_error_html(
                request=request,
                status_code=500,
                message=f"模板渲染错误: {e}",
                debug=debug,
                is_htmx=False,
            )
            return HTMLResponse(html, status_code=500)

        return HTMLResponse(html)

    # 手动设置签名（替代 FastAPI 自动推断 **kwargs）
    handler.__signature__ = inspect.Signature(parameters=sig_params)
    handler.__name__ = f"page_{route_path.strip('/').replace('/', '_') or 'root'}"

    app.get(route_path, response_class=HTMLResponse)(handler)
