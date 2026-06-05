"""
错误处理 — 开发友好的异常展示

改进（v0.3.0）：
- 401 异常时 HTMX 请求自动返回 HX-Redirect 到登录页
- 401 异常时非 HTMX 请求返回 meta refresh 重定向

使用方式：
    from pynuxt.errors import BFFError, render_error_html, setup_exception_handlers
    setup_exception_handlers(app, debug=DEBUG, login_path="/login")
"""

import traceback

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from pynuxt.templates import env


class BFFError(Exception):
    """BFF 业务异常（带 HTTP 状态码）"""

    def __init__(self, message: str, status_code: int = 500, detail: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}


def _format_traceback(exc: Exception) -> str:
    """格式化 traceback 为 HTML"""
    tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb_text = "".join(tb_lines)
    # 转义 HTML 特殊字符
    tb_text = tb_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return tb_text


def _extract_request_info(request: Request) -> dict:
    """提取请求信息用于错误展示"""
    return {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "client": str(request.client) if request.client else "N/A",
    }


def render_error_html(
    request: Request,
    status_code: int,
    message: str,
    exc: Exception = None,
    debug: bool = False,
    is_htmx: bool = False,
) -> str:
    """渲染错误页面 HTML"""
    context = {
        "status_code": status_code,
        "message": message,
        "debug": debug,
        "is_htmx": is_htmx,
        "request_info": _extract_request_info(request) if debug else None,
    }

    if debug and exc:
        context["exc_type"] = type(exc).__name__
        context["exc_message"] = str(exc)
        context["traceback"] = _format_traceback(exc)

    try:
        template = env.get_template("pages/error.html")
        return template.render(**context)
    except Exception:
        # 模板渲染失败时的兜底
        if debug:
            tb = traceback.format_exc()
            return f"""
            <div style="padding: 20px; font-family: monospace; background: #1a1a2e; color: #eee;">
                <h1 style="color: #e94560;">错误 (HTTP {status_code})</h1>
                <p><strong>{type(exc).__name__ if exc else 'Error'}:</strong> {message}</p>
                <pre style="background: #16213e; padding: 15px; overflow-x: auto; white-space: pre-wrap;">{tb}</pre>
            </div>
            """
        return f"""
        <div style="padding: 20px; text-align: center;">
            <h1>出错了 (HTTP {status_code})</h1>
            <p>{message}</p>
            <a href="/">返回首页</a>
        </div>
        """


def _is_htmx_request(request: Request) -> bool:
    """判断是否是 HTMX 请求"""
    return request.headers.get("HX-Request") == "true"


def setup_exception_handlers(app: FastAPI, debug: bool = False, login_path: str = "/login"):
    """在 FastAPI 应用上注册全局异常处理器

    Args:
        app: FastAPI 实例
        debug: 是否开启调试模式
        login_path: 登录页路径（401 重定向目标，v0.3.0 新增）
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """处理 HTTP 异常"""
        is_htmx = _is_htmx_request(request)

        # v0.3.0: 401 时自动重定向到登录页
        if exc.status_code == 401:
            if is_htmx:
                # HTMX 请求：返回 HX-Redirect 头
                return HTMLResponse(
                    content="",
                    status_code=401,
                    headers={"HX-Redirect": login_path}
                )
            else:
                # 普通请求：meta refresh 重定向
                html = f'<meta http-equiv="refresh" content="0;url={login_path}">'
                return HTMLResponse(content=html, status_code=401)

        html = render_error_html(
            request=request,
            status_code=exc.status_code,
            message=exc.detail or "请求出错",
            debug=debug,
            is_htmx=is_htmx,
        )
        if is_htmx and exc.status_code >= 500:
            html = f'<div class="error-inline" hx-trigger="load">{html}</div>'
        return HTMLResponse(content=html, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求参数验证异常"""
        is_htmx = _is_htmx_request(request)
        errors = exc.errors()
        message = "请求参数验证失败"
        if debug:
            message += f": {errors}"
        html = render_error_html(
            request=request,
            status_code=422,
            message=message,
            exc=exc if debug else None,
            debug=debug,
            is_htmx=is_htmx,
        )
        return HTMLResponse(content=html, status_code=422)

    @app.exception_handler(BFFError)
    async def bff_error_handler(request: Request, exc: BFFError):
        """处理 BFF 业务异常"""
        is_htmx = _is_htmx_request(request)

        # v0.3.0: BFFError 401 也重定向到登录
        if exc.status_code == 401:
            if is_htmx:
                return HTMLResponse(
                    content="",
                    status_code=401,
                    headers={"HX-Redirect": login_path}
                )
            else:
                html = f'<meta http-equiv="refresh" content="0;url={login_path}">'
                return HTMLResponse(content=html, status_code=401)

        html = render_error_html(
            request=request,
            status_code=exc.status_code,
            message=exc.message,
            exc=exc if debug else None,
            debug=debug,
            is_htmx=is_htmx,
        )
        return HTMLResponse(content=html, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """兜底：处理所有未捕获异常"""
        is_htmx = _is_htmx_request(request)
        html = render_error_html(
            request=request,
            status_code=500,
            message="服务器内部错误",
            exc=exc,
            debug=debug,
            is_htmx=is_htmx,
        )
        return HTMLResponse(content=html, status_code=500)


# ===== 快捷函数 =====

def api_error(status_code: int, message: str, detail: dict = None):
    """抛出 BFF 业务异常（用在 BFF 子类中）"""
    raise BFFError(message, status_code, detail)
