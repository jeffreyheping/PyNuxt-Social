"""帖子 API Mixin — get_posts / create_post / toggle_like"""
from __future__ import annotations

from services._base import ApiBase


class PostMixin(ApiBase):
    """帖子相关 API"""

    async def get_posts(self, feed: str = "global", skip: int = 0, limit: int = 20) -> list:
        return await self._get("/api/posts", {"feed": feed, "skip": skip, "limit": limit})

    async def create_post(self, content: str) -> dict:
        return await self._post("/api/posts", {"content": content})

    async def toggle_like(self, post_id: int) -> dict:
        return await self._post(f"/api/posts/{post_id}/like", {})
