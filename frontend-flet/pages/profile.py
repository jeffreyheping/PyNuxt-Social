"""用户主页

替代: frontend/pages/users/[username]/index.html + components/profile_header.html

功能:
- 用户档案信息（头像/昵称/@username/加入时间/统计数据）
- 与当前用户的关系按钮（加好友/已是好友/接受请求）
- 用户的帖子列表
- Tab 切换: 帖子 / 粉丝 / 关注
"""
from __future__ import annotations

import flet as ft
from components.layout import layout, spinner, empty_state
from components.post_card import post_card
from components.user_card import user_card


def render_profile(page: ft.Page, api, username: str) -> ft.Control:
    # 顶部状态容器
    header_container = ft.Container(content=spinner("加载用户信息..."))
    posts_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
    followers_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    following_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    active_tab = {"value": "posts"}

    # —— Tab 按钮 ——
    tab_posts = ft.TextButton("帖子", on_click=lambda e: _switch_tab("posts"))
    tab_followers = ft.TextButton("粉丝", on_click=lambda e: _switch_tab("followers"))
    tab_following = ft.TextButton("关注", on_click=lambda e: _switch_tab("following"))

    content_area = ft.Column([], expand=True, spacing=8)

    def _switch_tab(tab: str):
        active_tab["value"] = tab
        _render_content()

    def _render_content():
        # 先清掉旧内容，然后根据 tab 填充
        content_area.controls = []
        content_area.update()
        if active_tab["value"] == "posts":
            content_area.controls = [posts_column]
            page.run_task(_load_posts())
        elif active_tab["value"] == "followers":
            content_area.controls = [followers_column]
            page.run_task(_load_followers())
        else:
            content_area.controls = [following_column]
            page.run_task(_load_following())
        content_area.update()

    # —— 加载用户主页信息 ——
    async def _load_profile():
        try:
            user = await api.get_user_profile(username)
            display = user.get("display_name") or user.get("username", username)
            post_count = user.get("post_count", 0)
            follower_count = user.get("follower_count", 0)
            following_count = user.get("following_count", 0)
            created_at = user.get("created_at", "")

            # 查好友状态（仅登录用户 & 且不是自己）
            friend_btn_text = "加载中..."
            friend_btn_callback = None
            friend_btn_disabled = True
            is_self = False
            if api.is_logged_in:
                try:
                    st = await api.get_friend_status(username)
                    status = st.get("status", "none")
                    if status == "self":
                        is_self = True
                    elif status == "accepted":
                        friend_btn_text = "✓ 已是好友"
                    elif status == "pending":
                        friend_btn_text = "已发送请求"
                    elif status == "pending_received":
                        friend_btn_text = "接受请求"
                        friend_btn_callback = _accept_request
                        friend_btn_disabled = False
                    elif status == "rejected":
                        friend_btn_text = "已被拒绝"
                    else:
                        friend_btn_text = "加好友"
                        friend_btn_callback = _send_request
                        friend_btn_disabled = False
                except Exception:
                    friend_btn_text = ""

            self_label = ft.Text("（这是你自己）", color=ft.Colors.OUTLINE, size=14) if is_self else None

            friend_btn_control = ft.TextButton(friend_btn_text, disabled=friend_btn_disabled, on_click=friend_btn_callback) if friend_btn_text else None

            header = ft.Container(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.CircleAvatar(
                                    content=ft.Text(str(display)[0].upper(), weight=ft.FontWeight.BOLD),
                                    radius=32,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(display, size=22, weight=ft.FontWeight.BOLD),
                                        ft.Text(f"@{username}", color=ft.Colors.OUTLINE, size=13),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                *(self_label and [self_label]),
                                *(friend_btn_control and [friend_btn_control]),
                            ],
                            spacing=16,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(height=8),
                        ft.Row(
                            [
                                ft.Text(f"帖子 {post_count}"),
                                ft.VerticalDivider(width=20),
                                ft.Text(f"粉丝 {follower_count}"),
                                ft.VerticalDivider(width=20),
                                ft.Text(f"关注 {following_count}"),
                            ],
                            spacing=8,
                        ),
                        ft.Row([ft.Text(f"加入于 {created_at}", color=ft.Colors.OUTLINE, size=12)]),
                    ],
                    spacing=4,
                ),
                padding=16,
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                border_radius=12,
            )

            header_container.content = header
            header_container.update()

            # 默认加载帖子
            _switch_tab("posts")

        except Exception as ex:
            header_container.content = ft.Text(f"加载用户失败: {ex}", color=ft.Colors.ERROR)
            header_container.update()

    async def _load_posts():
        posts_column.controls = [spinner("加载帖子...")]
        posts_column.update()
        try:
            posts = await api.get_user_posts(username)
            if not posts:
                posts_column.controls = [empty_state("还没有发过帖子")]
            else:
                posts_column.controls = [post_card(p, api) for p in posts]
        except Exception as ex:
            posts_column.controls = [ft.Text(f"加载失败: {ex}", color=ft.Colors.ERROR)]
        posts_column.update()

    async def _load_followers():
        followers_column.controls = [spinner("加载粉丝...")]
        followers_column.update()
        try:
            users = await api.get_followers(username)
            if not users:
                followers_column.controls = [empty_state("还没有粉丝")]
            else:
                followers_column.controls = [
                    user_card(u, api, show_friend_button=True) for u in users
                ]
                for c in followers_column.controls:
                    load_fn = (c.data or {}).get("load_status")
                    if load_fn:
                        try:
                            await load_fn()
                        except Exception:
                            pass
        except Exception as ex:
            followers_column.controls = [ft.Text(f"加载失败: {ex}", color=ft.Colors.ERROR)]
        followers_column.update()

    async def _load_following():
        following_column.controls = [spinner("加载关注...")]
        following_column.update()
        try:
            users = await api.get_following(username)
            if not users:
                following_column.controls = [empty_state("还没有关注任何人")]
            else:
                following_column.controls = [
                    user_card(u, api, show_friend_button=True) for u in users
                ]
                for c in following_column.controls:
                    load_fn = (c.data or {}).get("load_status")
                    if load_fn:
                        try:
                            await load_fn()
                        except Exception:
                            pass
        except Exception as ex:
            following_column.controls = [ft.Text(f"加载失败: {ex}", color=ft.Colors.ERROR)]
        following_column.update()

    # ---- 好友操作 ----
    async def _accept_request_impl():
        try:
            # 从收到的请求里找到对应 id
            requests = await api.get_friend_requests()
            for r in requests:
                from_user = r.get("from_user", {}) or {}
                if from_user.get("username") == username:
                    await api.accept_friend_request(r["id"])
                    page.show_snack_bar(ft.SnackBar(ft.Text("已接受好友请求")))
                    page.run_task(_load_profile())
                    return
            page.show_snack_bar(ft.SnackBar(ft.Text("找不到对应的请求")))
        except Exception as ex:
            page.show_snack_bar(ft.SnackBar(ft.Text(f"操作失败: {ex}")))

    def _accept_request(e):
        page.run_task(_accept_request_impl())

    async def _send_request_impl():
        try:
            await api.send_friend_request(username)
            page.show_snack_bar(ft.SnackBar(ft.Text("已发送好友请求")))
            page.run_task(_load_profile())
        except Exception as ex:
            page.show_snack_bar(ft.SnackBar(ft.Text(f"发送失败: {ex}")))

    def _send_request(e):
        page.run_task(_send_request_impl())

    body = [
        header_container,
        ft.Row([tab_posts, tab_followers, tab_following], spacing=4),
        content_area,
    ]

    page.run_task(_load_profile())
    return layout(page, api, title="", content=body)
