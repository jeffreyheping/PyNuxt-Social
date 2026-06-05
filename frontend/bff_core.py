"""BFF 业务层

继承 BFFBase，用 @get/@post/@put 装饰器声明路由。
BFF 方法 = 路由 + 业务逻辑 + 渲染，一处搞定。

4 个业务 BFF：
- AuthBFF：注册/登录/登出/状态（路由留在 main.py，因为要操作 Cookie）
- FeedBFF：动态流/发帖/点赞
- UserBFF：用户搜索/主页/粉丝关注
- FriendBFF：好友请求/关系状态
"""
from fastapi import Form, Query

from pynuxt.bff import BFFBase, get, post, put


class AuthBFF(BFFBase):
    """认证业务 BFF

    login/register 不用 @route 装饰器——它们需要操作 Cookie，
    Cookie 是前端服务器的专属职责，留在 main.py 手动注册。
    """

    async def login(self, username: str, password: str) -> dict:
        """登录：返回后端 Token"""
        return await self._post("/api/auth/login", {
            "username": username, "password": password
        })

    async def register(self, username: str, email: str, password: str, display_name: str = None) -> dict:
        """注册：返回后端 Token"""
        data = {"username": username, "email": email, "password": password}
        if display_name:
            data["display_name"] = display_name
        return await self._post("/api/auth/register", data)

    def get_status_html(self, user: dict | None) -> str:
        """返回导航栏登录状态 HTML 片段（走模板渲染）"""
        return self._render("components/auth_status.html", user=user)


class FeedBFF(BFFBase):
    """动态流业务 BFF"""
    prefix = "/bff/posts"

    @get("", auth="optional")
    async def get_posts(
        self,
        feed: str = Query("global"),
        skip: int = Query(0),
        limit: int = Query(20),
    ) -> str:
        """获取动态流并渲染帖子列表"""
        posts = await self._get("/api/posts", params={"feed": feed, "skip": skip, "limit": limit})
        return self._render(
            "components/post_list.html",
            data=posts,
            current_user_id=self.current_user_id,
            current_feed=feed,
        )

    @post("", auth="required")
    async def create_post(
        self,
        content: str = Form(...),
        feed: str = Query("global"),
    ) -> str:
        """发帖后刷新列表"""
        await self._post("/api/posts", {"content": content})
        posts = await self._get("/api/posts", params={"feed": feed})
        return self._render(
            "components/post_list.html",
            data=posts,
            current_user_id=self.current_user_id,
            current_feed=feed,
        )

    @post("/{post_id}/like", auth="token")
    async def toggle_like(self, post_id: int) -> str:
        """点赞/取消赞，返回按钮片段"""
        result = await self._post(f"/api/posts/{post_id}/like", {})
        return self._render(
            "components/like_button.html",
            post_id=post_id,
            liked=result["liked"],
            like_count=result["like_count"],
        )


class UserBFF(BFFBase):
    """用户业务 BFF"""
    prefix = "/bff/users"

    @get("/search", auth="token")
    async def search_users(self, q: str = Query("")) -> str:
        """搜索用户，返回结果片段"""
        if not q:
            return '<div class="empty-state"><p>输入关键词搜索用户</p></div>'
        users = await self._get("/api/users", params={"q": q})
        return self._render("components/search_results.html", data=users)

    @get("/{username}/profile", auth="optional")
    async def get_user_profile(self, username: str) -> str:
        """获取用户详情，返回 header 片段"""
        user = await self._get(f"/api/users/{username}")
        return self._render(
            "components/profile_header.html",
            data=user,
            current_user_id=self.current_user_id,
        )

    @get("/{username}/posts", auth="optional")
    async def get_user_posts(
        self,
        username: str,
        skip: int = Query(0),
        limit: int = Query(20),
    ) -> str:
        """获取某用户的帖子"""
        posts = await self._get(f"/api/users/{username}/posts", params={"skip": skip, "limit": limit})
        return self._render(
            "components/post_list.html",
            data=posts,
            current_user_id=self.current_user_id,
            current_feed="global",
        )

    @get("/{username}/followers", auth="token")
    async def get_followers(self, username: str) -> str:
        """获取粉丝列表"""
        users = await self._get(f"/api/users/{username}/followers")
        return self._render("components/user_card.html", data=users, list_type="粉丝")

    @get("/{username}/following", auth="token")
    async def get_following(self, username: str) -> str:
        """获取关注列表"""
        users = await self._get(f"/api/users/{username}/following")
        return self._render("components/user_card.html", data=users, list_type="关注")


class FriendBFF(BFFBase):
    """好友业务 BFF"""
    prefix = "/bff/friends"

    @get("/requests", auth="token")
    async def get_pending_requests(self) -> str:
        """获取待处理好友请求"""
        requests = await self._get("/api/friends/requests")
        return self._render("components/friend_request_list.html", data=requests)

    @post("/requests/{username}", auth="token")
    async def send_request(self, username: str) -> str:
        """发送好友请求，返回更新后的好友按钮"""
        await self._post(f"/api/friends/requests/{username}", {})
        return self._render("components/friend_button.html", status="pending", username=username)

    @put("/requests/{request_id}", auth="token")
    async def respond_request(
        self,
        request_id: int,
        action: str = Form(...),
    ) -> str:
        """接受/拒绝好友请求"""
        await self._put(f"/api/friends/requests/{request_id}", {"action": action})
        requests = await self._get("/api/friends/requests")
        return self._render("components/friend_request_list.html", data=requests)

    @get("/status/{username}", auth="token")
    async def get_friend_status(self, username: str) -> str:
        """获取好友关系状态按钮"""
        result = await self._get(f"/api/friends/status/{username}")
        return self._render("components/friend_button.html", status=result["status"], username=username)
