"""前端 FastAPI BFF 入口

Auth 路由手动注册（Cookie 操作是 BFF 层专属职责）。
其他 BFF 路由通过 register() 自动注册（一行搞定）。
页面路由由 pynuxt.routing 自动映射。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, Depends
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
import logging

from config import (
    API_BASE, TEMPLATE_DIRS, PAGES_DIR, DEBUG,
    SITE_NAME, AUTH_COOKIE_NAME, AUTH_COOKIE_MAX_AGE,
    PROTECTED_PATHS, LOGIN_PATH,
)
from bff_core import AuthBFF, FeedBFF, UserBFF, FriendBFF
from pynuxt.bff import BFFBase
from pynuxt.routing import install_file_routing
from pynuxt.auth import get_optional_user, get_context_user
from pynuxt.templates import env, configure_env
from pynuxt.errors import setup_exception_handlers
from pynuxt.middleware import LoginGuardMiddleware

logger = logging.getLogger(__name__)

# ==================== Lifespan（启动/关闭钩子）====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：关闭时清理共享 httpx 客户端"""
    yield
    await BFFBase.close_all()
    logger.info("BFF 共享 httpx 客户端已关闭")


# ==================== 初始化 ====================

app = FastAPI(title=f"{SITE_NAME} Frontend", lifespan=lifespan)

# 注册全局异常处理器（401 自动重定向到登录页）
setup_exception_handlers(app, debug=DEBUG, login_path=LOGIN_PATH)

# 登录态守卫中间件
app.add_middleware(
    LoginGuardMiddleware,
    login_path=LOGIN_PATH,
    protected_paths=PROTECTED_PATHS,
    cookie_name=AUTH_COOKIE_NAME,
)

# 配置模板环境（注入全局变量 + 调试模式）
configure_env(
    template_dirs=TEMPLATE_DIRS,
    globals={"site_name": SITE_NAME},
    debug=DEBUG,
)

# 静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")


# ==================== BFF 路由注册（核心：一行一个）====================

auth_bff = AuthBFF()

FeedBFF.register(app, API_BASE)
UserBFF.register(app, API_BASE)
FriendBFF.register(app, API_BASE)


# ==================== Auth 路由（手动注册，因为要操作 Cookie）====================

def _set_auth_cookie(response: Response, token: str) -> Response:
    """在响应中设置认证 Cookie"""
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=AUTH_COOKIE_MAX_AGE,
    )
    return response


def _clear_auth_cookie(response: Response) -> Response:
    """在响应中清除认证 Cookie"""
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/")
    return response


@app.post("/bff/auth/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """登录：BFF 调后端 API → 设 Cookie → HX-Redirect"""
    try:
        result = await auth_bff.login(username, password)
        token = result.get("access_token")
        response = Response(content="", status_code=200)
        _set_auth_cookie(response, token)
        response.headers["HX-Redirect"] = "/feed"
        return response
    except Exception:
        return HTMLResponse('<div class="error-message">登录失败，请检查用户名和密码</div>')


@app.post("/bff/auth/register")
async def register(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(None),
):
    """注册：BFF 调后端 API → 设 Cookie → HX-Redirect"""
    try:
        result = await auth_bff.register(username, email, password, display_name)
        token = result.get("access_token")
        response = Response(content="", status_code=200)
        _set_auth_cookie(response, token)
        response.headers["HX-Redirect"] = "/feed"
        return response
    except Exception as e:
        logger.error(f"注册失败: {e}")
        return HTMLResponse('<div class="error-message">注册失败，用户名或邮箱可能已存在</div>')


@app.post("/bff/auth/logout")
async def logout():
    """登出：清 Cookie → HX-Redirect"""
    response = Response(content="", status_code=200)
    _clear_auth_cookie(response)
    response.headers["HX-Redirect"] = "/"
    return response


@app.get("/bff/auth/status", response_class=HTMLResponse)
async def auth_status(user: dict | None = Depends(get_optional_user)):
    """导航栏登录状态片段"""
    return auth_bff.get_status_html(user)


# ==================== 文件系统路由 ====================

async def _context_vars(request):
    """页面渲染时的额外上下文：注入 current_user"""
    user = await get_context_user(request)
    return {"current_user": user}


install_file_routing(app, env, pages_dir=PAGES_DIR, context_vars=_context_vars, debug=DEBUG)
