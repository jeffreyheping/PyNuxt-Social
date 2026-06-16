"""认证 API Mixin — login / register / logout / fetch_me"""
from __future__ import annotations

import httpx

from services._base import ApiBase


class AuthMixin(ApiBase):
    """认证相关 API"""

    async def login(self, username: str, password: str) -> dict:
        """返回: {"access_token": "...", "token_type": "bearer", "user": {...}}"""
        return await self._post("/api/auth/login", {"username": username, "password": password})

    async def register(self, username: str, email: str, password: str, display_name: str = "") -> dict:
        data = {"username": username, "email": email, "password": password}
        if display_name:
            data["display_name"] = display_name
        return await self._post("/api/auth/register", data)

    async def logout(self) -> dict:
        result = await self._post("/api/auth/logout", {})
        self.token = None
        self.current_user = None
        return result

    async def fetch_me(self) -> dict | None:
        """从 /api/auth/me 拉取当前用户信息"""
        if not self.token:
            return None
        try:
            return await self._get("/api/auth/me")
        except httpx.HTTPError:
            return None
