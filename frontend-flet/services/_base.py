"""API 服务层 — HTTP 基础能力

提供 httpx AsyncClient 的懒初始化、通用 HTTP 方法、认证头、token 管理。
所有领域 Mixin 继承此基类。
"""
from __future__ import annotations

import httpx
import os

API_BASE = os.getenv("API_BASE", "http://localhost:8012")


class ApiBase:
    """HTTP 基础能力：连接管理 + 通用请求方法 + token 状态"""

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
