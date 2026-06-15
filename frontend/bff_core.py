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

from pynuxt.bff import BFFBase, get, post, put, CrudAction


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
        full: bool = Query(False),
        skip: int = Query(0),
        limit: int = Query(20),
    ) -> str:
        """获取动态流；full=True 返回完整组件，否则只返回帖子列表"""
        posts = await self._get("/api/posts", params={"feed": feed, "skip": skip, "limit": limit})
        template = "components/feed_content.html" if full else "components/post_list.html"
        return self._render(
            template,
            data=posts,
            current_user_id=self.current_user_id,
            current_feed=feed,
        )

    @post("", auth="required")
    async def create_post(
        self,
        content: str = Form(...),
        feed: str = Form("global"),
    ) -> str:
        """发帖后返回完整组件（outerHTML 替换，表单自动清空）"""
        await self._post("/api/posts", {"content": content})
        posts = await self._get("/api/posts", params={"feed": feed})
        return self._render(
            "components/feed_content.html",
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
    """用户业务 BFF — 混合写法"""
    prefix = "/bff/users"

    # 有 BFF 层业务逻辑（空查询守卫）→ 保留装饰器
    @get("/search", auth="token")
    async def search_users(self, q: str = Query("")) -> str:
        """搜索用户，返回结果片段"""
        if not q:
            return '<div class="empty-state"><p>输入关键词搜索用户</p></div>'
        users = await self._get("/api/users", params={"q": q})
        return self._render("components/search_results.html", data=users)

    # 纯透传 → CrudAction 声明式
    profile = CrudAction(
        backend="/api/users/{username}",
        template="components/profile_header.html",
        auth="optional",
        path="/{username}/profile",
    )
    posts = CrudAction(
        backend="/api/users/{username}/posts",
        template="components/post_list.html",
        auth="optional",
        path="/{username}/posts",
        template_context={"current_feed": "global"},
    )
    followers = CrudAction(
        backend="/api/users/{username}/followers",
        template="components/user_card.html",
        auth="token",
        path="/{username}/followers",
        template_context={"list_type": "粉丝"},
    )
    following = CrudAction(
        backend="/api/users/{username}/following",
        template="components/user_card.html",
        auth="token",
        path="/{username}/following",
        template_context={"list_type": "关注"},
    )


class FriendBFF(BFFBase):
    """好友业务 BFF — CrudAction 声明式写法"""
    prefix = "/bff/friends"

    list = CrudAction(
        backend="/api/friends/requests",
        template="components/friend_request_list.html",
        auth="token",
        path="/requests",
    )
    send = CrudAction(
        backend="/api/friends/requests/{username}",
        method="POST",
        template="components/friend_button.html",
        auth="token",
        path="/requests/{username}",
        template_context={"status": "pending"},
    )
    respond = CrudAction(
        backend="/api/friends/requests/{request_id}",
        method="PUT",
        refresh="list",
        auth="token",
        path="/requests/{request_id}",
    )
    status = CrudAction(
        backend="/api/friends/status/{username}",
        template="components/friend_button.html",
        auth="token",
        path="/status/{username}",
    )
