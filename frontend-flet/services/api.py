"""API 服务层 — httpx 封装，供所有页面/组件调用

一个 ApiClient 实例 = 一个 Flet 会话。token 存在实例里。
"""
from __future__ import annotations

import httpx
import os

API_BASE = os.getenv("API_BASE", "http://localhost:8012")


class ApiClient:
    """封装对 FastAPI 后端的所有 REST API 调用"""

    def __init__(self, base_url: str = API_BASE):
        self.base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None
        self.token: str | None = None
        self.current_user: dict | None = None

    # ── httpx client（懒初始化） ─────────────────────────────
    def _get_http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=10.0,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ── 通用 HTTP ─────────────────────────────────────────────
    def _headers(self) -> dict:
        h = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def _get(self, path: str, params: dict | None = None) -> dict | list:
        resp = await self._get_http().get(path, params=params, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def _post(self, path: str, data: dict | None = None) -> dict | list:
        resp = await self._get_http().post(path, json=data, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def _put(self, path: str, data: dict | None = None) -> dict | list:
        resp = await self._get_http().put(path, json=data, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def _delete(self, path: str) -> dict | list:
        resp = await self._get_http().delete(path, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    # ── 属性 ───────────────────────────────────────────────────
    @property
    def is_logged_in(self) -> bool:
        return self.token is not None

    # ── 认证 API ───────────────────────────────────────────────
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

    # ── 帖子 API ───────────────────────────────────────────────
    async def get_posts(self, feed: str = "global", skip: int = 0, limit: int = 20) -> list:
        return await self._get("/api/posts", {"feed": feed, "skip": skip, "limit": limit})

    async def create_post(self, content: str) -> dict:
        return await self._post("/api/posts", {"content": content})

    async def toggle_like(self, post_id: int) -> dict:
        return await self._post(f"/api/posts/{post_id}/like", {})

    # ── 用户 API ───────────────────────────────────────────────
    async def search_users(self, q: str) -> list:
        return await self._get("/api/users", {"q": q})

    async def get_user_profile(self, username: str) -> dict:
        return await self._get(f"/api/users/{username}")

    async def get_user_posts(self, username: str, skip: int = 0, limit: int = 20) -> list:
        return await self._get(f"/api/users/{username}/posts", {"skip": skip, "limit": limit})

    async def get_followers(self, username: str) -> list:
        return await self._get(f"/api/users/{username}/followers")

    async def get_following(self, username: str) -> list:
        return await self._get(f"/api/users/{username}/following")

    # ── 好友 API ───────────────────────────────────────────────
    async def get_friend_requests(self) -> list:
        return await self._get("/api/friends/requests")

    async def send_friend_request(self, username: str) -> dict:
        return await self._post(f"/api/friends/requests/{username}", {})

    async def accept_friend_request(self, request_id: int) -> dict:
        return await self._put(f"/api/friends/requests/{request_id}", {"action": "accept"})

    async def reject_friend_request(self, request_id: int) -> dict:
        return await self._put(f"/api/friends/requests/{request_id}", {"action": "reject"})

    async def get_friend_status(self, username: str) -> dict:
        """返回关系状态: none / pending / pending_received / accepted / rejected / self"""
        return await self._get(f"/api/friends/status/{username}")
