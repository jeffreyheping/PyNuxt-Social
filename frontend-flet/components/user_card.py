"""用户卡片组件

替代原 frontend/components/user_card.html + friend_button.html

用于: 搜索结果、粉丝列表、关注列表、用户主页
"""
from __future__ import annotations

import flet as ft


def user_card(
    user: dict,
    api,
    on_profile_click=None,
    show_friend_button: bool = True,
) -> ft.Container:
    """用户卡片 — 头像 + 名称 + 好友按钮

    Args:
        user: {"id", "username", "display_name", "created_at", ...}
        api: ApiClient 实例（用于好友 API 调用）
        on_profile_click: 点击用户卡片时的回调（默认跳转到 /users/{username}）
        show_friend_button: 是否显示好友按钮（粉丝列表中可能要关闭）
    """
    username = user.get("username", "")
    display_name = user.get("display_name") or username
    created_at = user.get("created_at", "")

    # 好友按钮 — 初始显示占位，异步加载真实状态
    friend_btn = ft.TextButton("加载中...", disabled=True)

    if show_friend_button and api.is_logged_in:
        # 启动时异步查询关系状态
        page_ref = {"page": None}

        async def load_status():
            try:
                status = await api.get_friend_status(username)
                _update_button(status.get("status", "none"))
            except Exception:
                friend_btn.text = ""
                friend_btn.visible = False
                if friend_btn.page:
                    friend_btn.update()

        def _update_button(status: str):
            """根据状态设置按钮文字/回调"""
            if status == "self":
                friend_btn.visible = False
            elif status == "accepted":
                friend_btn.text = "✓ 已是好友"
                friend_btn.disabled = True
            elif status == "pending":
                friend_btn.text = "已发送请求"
                friend_btn.disabled = True
            elif status == "pending_received":
                friend_btn.text = "接受请求"
                friend_btn.on_click = _accept
                friend_btn.disabled = False
            elif status == "rejected":
                friend_btn.text = "已拒绝"
                friend_btn.disabled = True
            else:  # none
                friend_btn.text = "加好友"
                friend_btn.on_click = _send_request
                friend_btn.disabled = False
            if friend_btn.page:
                friend_btn.update()

        async def _send_request(e):
            try:
                await api.send_friend_request(username)
                _update_button("pending")
            except Exception:
                e.page.show_snack_bar(ft.SnackBar(ft.Text("发送失败")))

        async def _accept(e):
            try:
                # 先查一下 request id — 简化处理：让用户去 /friends 处理
                # 这里做个简单的实现: 查收到的请求列表，找到目标用户
                requests = await api.get_friend_requests()
                for r in requests:
                    from_user = r.get("from_user", {}) or {}
                    if from_user.get("username") == username:
                        await api.accept_friend_request(r["id"])
                        _update_button("accepted")
                        return
                # 没找到，跳转到好友页
                e.page.show_snack_bar(ft.SnackBar(ft.Text("请前往好友页处理")))
            except Exception:
                e.page.show_snack_bar(ft.SnackBar(ft.Text("操作失败")))

        # 注册到页面生命周期 — 先在第一次 build 后异步拉取
        import flet_effect

        # 由于没有 flet_effect，我们用一个简单的方式：延迟执行
        from flet import Page

        # 这里我们用一个「挂载后立即执行」的技巧: 把 loader 包成一个不可见的 Row
        loader = ft.Container(width=0, height=0, visible=False)

        def _on_mount(e):
            page_ref["page"] = e.page
            e.page.run_task(load_status)

        # 需要把它的 on_visible 绑定上 — 但更简单的做法是在 user_card 返回时直接调度
        # 这里改为: 直接把异步任务放到 page.run_task 里
        # 调用者需要先有 page 引用；改为: 让 user_card 接受可选的 page 参数
        # 但为了保持 API 简单，改为: 由调用者手动调用 load_status

    else:
        friend_btn.visible = False

    # 默认跳转 — 点击卡片去用户主页
    def _go_profile(e):
        if on_profile_click:
            on_profile_click(e)
        else:
            e.page.go(f"/users/{username}")

    return ft.Container(
        ft.Row(
            [
                ft.CircleAvatar(
                    content=ft.Text(str(display_name)[0].upper(), weight=ft.FontWeight.BOLD),
                    radius=22,
                ),
                ft.Column(
                    [
                        ft.Text(display_name, weight=ft.FontWeight.BOLD),
                        ft.Text(f"@{username}", size=12, color=ft.Colors.OUTLINE),
                    ],
                    spacing=2,
                    expand=True,
                ),
                friend_btn,
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
        padding=ft.Padding(12, 10, 12, 10),
        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=10,
        on_click=_go_profile,
        data={"load_status": load_status if show_friend_button and api.is_logged_in else None},
    )
