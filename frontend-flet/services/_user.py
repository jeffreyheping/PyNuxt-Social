"""用户 API Mixin — search / profile / posts / followers / following"""
from __future__ import annotations

from services._base import ApiBase


class UserMixin(ApiBase):
    """用户相关 API"""

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
