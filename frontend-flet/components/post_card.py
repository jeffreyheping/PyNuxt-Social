"""帖子卡片组件

替代原 frontend/components/post_item.html + like_button.html
"""
from __future__ import annotations

import flet as ft


def post_card(
    post: dict,
    api,
    on_like_changed=None,
) -> ft.Container:
    """单条帖子的卡片

    Args:
        post: 后端返回的帖子 dict: {"id", "author", "content", "created_at", "like_count", "liked_by_me"}
        api: ApiClient 实例（用于点赞/取消赞 API 调用）
        on_like_changed: 点赞状态变化后的回调（父页可以刷新列表）
    """
    author = post.get("author", {})
    author_name = author.get("display_name") or author.get("username", "未知用户")
    author_username = author.get("username", "")
    content_text = post.get("content", "")
    like_count = post.get("like_count", 0)
    liked = post.get("liked_by_me", False)

    # 响应式点赞状态
    like_count_ref = {"value": like_count}  # 用 dict 让闭包可变
    liked_ref = {"value": liked}

    # 点赞按钮（图标 + 数字，Flet 0.85 的 IconButton 不支持 text 参数）
    like_icon_btn = ft.IconButton(
        icon=ft.Icons.FAVORITE_BORDER if not liked else ft.Icons.FAVORITE,
        icon_color=ft.Colors.RED if liked else None,
        tooltip="点赞",
        on_click=lambda e: _on_like(e),
    )
    like_count_text = ft.Text(str(like_count), size=12)
    like_btn = ft.Row([like_icon_btn, like_count_text], spacing=2, alignment=ft.MainAxisAlignment.CENTER)

    def _on_like(e):
        """点击点赞按钮 — 调用 API 并局部更新按钮状态"""
        page = e.page

        async def do_like():
            if not api.is_logged_in:
                page.go("/login")
                return
            try:
                result = await api.toggle_like(post["id"])
                # 更新状态
                liked_ref["value"] = result.get("liked", not liked_ref["value"])
                like_count_ref["value"] = result.get("like_count", like_count_ref["value"] + 1)
                like_icon_btn.icon = (
                    ft.Icons.FAVORITE_BORDER if not liked_ref["value"] else ft.Icons.FAVORITE
                )
                like_icon_btn.icon_color = ft.Colors.RED if liked_ref["value"] else None
                like_count_text.value = str(like_count_ref["value"])
                like_btn.update()
                if on_like_changed:
                    await on_like_changed()
            except Exception:
                page.show_snack_bar(ft.SnackBar(ft.Text("点赞失败")))

        page.run_task(do_like)

    def go_author_profile(e):
        if author_username:
            e.page.go(f"/users/{author_username}")

    return ft.Container(
        ft.Column(
            [
                # 头部: 头像 + 用户名 + 时间
                ft.Row(
                    [
                        ft.Stack(
                            [
                                ft.Container(
                                    on_click=go_author_profile,
                                    content=ft.Row(
                                        [
                                            ft.CircleAvatar(
                                                content=ft.Text(
                                                    str(author_name)[0].upper(),
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                                radius=18,
                                            ),
                                            ft.Text(author_name, weight=ft.FontWeight.BOLD),
                                        ],
                                        spacing=8,
                                    ),
                                    on_hover=lambda e: setattr(
                                        e.control, "mouse_cursor", ft.MouseCursor.CLICK if e.data == "true" else ft.MouseCursor.BASIC
                                    ),
                                )
                            ]
                        ),
                        ft.Text(post.get("created_at", ""), size=12, color=ft.Colors.OUTLINE),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    spacing=8,
                ),
                # 正文
                ft.Text(content_text, size=15, selectable=True),
                # 底部: 点赞按钮
                ft.Row(
                    [like_btn],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=4,
                ),
            ],
            spacing=10,
        ),
        padding=ft.Padding(16, 12, 16, 12),
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=12,
        bgcolor=ft.Colors.SURFACE,
        shadow=ft.BoxShadow(blur_radius=2, spread_radius=0, color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK)),
    )
