"""好友 API Mixin — requests / send / accept / reject / status"""
from __future__ import annotations

from services._base import ApiBase


class FriendMixin(ApiBase):
    """好友相关 API"""

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
