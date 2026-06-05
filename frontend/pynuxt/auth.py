"""认证工具 — FastAPI 依赖注入用

v0.5.0 改进：
- 请求级用户信息缓存：同一请求内多次调用 _get_user() 只打一次后端
- 与 contextvars 集成

提供 get_current_user_id / get_optional_user_id / get_token / get_optional_user，
供路由层通过 Depends() 自动注入用户 ID 或 Token。

支持两种 Token 来源：
1. Authorization Header（Bearer Token）
2. Cookie（auth_token）
"""

import httpx
from fastapi import Header, HTTPException, Cookie

from config import API_BASE, AUTH_COOKIE_NAME
from pynuxt.context import _user_cache, _UNSET

# 共享 httpx 客户端（用于调用后端 /api/auth/me）
_shared_client: httpx.AsyncClient | None = None


def _get_shared_client() -> httpx.AsyncClient:
    """获取共享 httpx 客户端（懒初始化）"""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(timeout=10.0)
    return _shared_client


def _extract_token(authorization: str = None, auth_token: str = None) -> str | None:
    """从 Header 或 Cookie 提取 Token"""
    if authorization and authorization.startswith("Bearer "):
        return authorization.replace("Bearer ", "")
    if auth_token:
        return auth_token
    return None


def get_token(
    authorization: str = Header(None),
    auth_token: str = Cookie(None, alias=AUTH_COOKIE_NAME)
) -> str | None:
    """获取 Token（可选，未登录返回 None）"""
    return _extract_token(authorization, auth_token)


async def get_current_user_id(
    authorization: str = Header(None),
    auth_token: str = Cookie(None, alias=AUTH_COOKIE_NAME)
) -> int:
    """从 JWT Token 获取用户 ID（强制，未登录 401）"""
    user = await _get_user(authorization, auth_token)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    return user["id"]


async def get_optional_user_id(
    authorization: str = Header(None),
    auth_token: str = Cookie(None, alias=AUTH_COOKIE_NAME)
) -> int | None:
    """从 JWT Token 获取用户 ID（可选，未登录返回 None）"""
    user = await _get_user(authorization, auth_token)
    return user["id"] if user else None


async def get_optional_user(
    authorization: str = Header(None),
    auth_token: str = Cookie(None, alias=AUTH_COOKIE_NAME)
) -> dict | None:
    """从 JWT Token 获取用户信息（可选，未登录返回 None）"""
    return await _get_user(authorization, auth_token)


async def _get_user(authorization: str = None, auth_token: str = None) -> dict | None:
    """内部：从后端 /api/auth/me 获取完整用户信息（请求级缓存）

    同一 HTTP 请求内，无论调用几次 _get_user()，只实际请求后端一次。
    缓存通过 contextvars 实现，ASGI 的 per-request Task 隔离保证请求间不泄漏。
    """
    # 请求级缓存命中
    cached = _user_cache.get()
    if cached is not _UNSET:
        return cached

    token = _extract_token(authorization, auth_token)
    if not token:
        _user_cache.set(None)
        return None

    client = _get_shared_client()
    try:
        response = await client.get(
            f"{API_BASE}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        result = response.json() if response.status_code == 200 else None
    except httpx.HTTPError:
        result = None

    _user_cache.set(result)
    return result


# ==================== 页面渲染辅助 ====================

async def get_context_user(request) -> dict | None:
    """从请求中提取当前用户（供 context_vars 使用）

    复用请求级缓存：如果 Depends 链已查过用户，此处直接返回。
    """
    auth_token = request.cookies.get(AUTH_COOKIE_NAME)
    if not auth_token:
        return None

    # 先检查缓存（可能已被 Depends 链填充）
    cached = _user_cache.get()
    if cached is not _UNSET:
        return cached

    # 缓存未命中，查询后端
    client = _get_shared_client()
    try:
        response = await client.get(
            f"{API_BASE}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        result = response.json() if response.status_code == 200 else None
    except httpx.HTTPError:
        result = None

    _user_cache.set(result)
    return result
