"""
登录态守卫中间件 — v0.3.0 新增

对指定路径前缀的请求检查登录状态，未登录则重定向到登录页。

适用于：受保护的页面路由（/feed, /friends 等），无需在每个 BFF 方法里手动检查。

使用方式：
    from pynuxt.middleware import LoginGuardMiddleware
    app.add_middleware(LoginGuardMiddleware, login_path="/login", protected_paths=["/feed", "/friends"])
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class LoginGuardMiddleware(BaseHTTPMiddleware):
    """登录态守卫中间件

    检查请求路径是否在 protected_paths 前缀列表中，
    如果是，验证 Cookie 中是否存在有效的 auth_token。
    未登录 → HTMX 请求返回 HX-Redirect，普通请求 302 重定向。

    注意：此中间件只做快速 Cookie 存在性检查（不验证 Token 有效性），
    Token 有效性由后端 API / BFF 层的 get_current_user_id 保证。
    对于需要精确鉴权的操作，仍需在 BFF 中使用 Depends(get_current_user_id)。
    """

    def __init__(
        self,
        app,
        login_path: str = "/login",
        protected_paths: list = None,
        cookie_name: str = "auth_token",
    ):
        super().__init__(app)
        self.login_path = login_path
        self.protected_paths = protected_paths or []
        self.cookie_name = cookie_name

    async def dispatch(self, request: Request, call_next) -> Response:
        # 只检查 GET 请求（页面导航），POST/PUT/DELETE 由 BFF 层处理
        if request.method != "GET":
            return await call_next(request)

        path = request.url.path

        # 检查是否需要登录
        needs_auth = any(path.startswith(prefix) for prefix in self.protected_paths)
        if not needs_auth:
            return await call_next(request)

        # 检查 Cookie 中是否有 Token
        auth_token = request.cookies.get(self.cookie_name)
        if auth_token:
            return await call_next(request)

        # 未登录：根据请求类型返回不同的重定向
        is_htmx = request.headers.get("HX-Request") == "true"
        if is_htmx:
            return Response(
                content="",
                status_code=401,
                headers={"HX-Redirect": self.login_path}
            )
        else:
            from starlette.responses import RedirectResponse
            return RedirectResponse(url=self.login_path, status_code=302)
