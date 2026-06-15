"""好友请求页面

替代: frontend/pages/friends.html + components/friend_request_item.html

展示当前用户收到的好友请求列表，可以接受/拒绝
"""
from __future__ import annotations

import flet as ft
from components.layout import layout, spinner, empty_state


def render_friends(page: ft.Page, api) -> ft.Control:
    if not api.is_logged_in:
        page.go("/login")
        return ft.Column([])

    requests_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    refresh_btn = ft.TextButton(
        "刷新",
        icon=ft.Icons.REFRESH,
        on_click=lambda e: page.run_task(_load_requests),
    )

    async def _load_requests():
        requests_column.controls = [spinner("加载请求...")]
        requests_column.update()
        try:
            reqs = await api.get_friend_requests()
            if not reqs:
                requests_column.controls = [empty_state("没有待处理的好友请求")]
            else:
                requests_column.controls = [_build_request_item(r) for r in reqs]
        except Exception as ex:
            requests_column.controls = [ft.Text(f"加载失败: {ex}", color=ft.Colors.ERROR)]
        requests_column.update()

    def _build_request_item(req: dict) -> ft.Container:
        from_user = req.get("from_user", {}) or {}
        uname = from_user.get("username", "未知用户")
        display = from_user.get("display_name") or uname
        created = req.get("created_at", "")

        status_text = ft.Text("待处理", color=ft.Colors.AMBER_400, size=12)

        def on_accept(e):
            async def do_accept():
                try:
                    await api.accept_friend_request(req["id"])
                    page.show_snack_bar(ft.SnackBar(ft.Text("已接受")))
                    page.run_task(_load_requests)
                except Exception as ex:
                    page.show_snack_bar(ft.SnackBar(ft.Text(f"失败: {ex}")))
            page.run_task(do_accept)

        def on_reject(e):
            async def do_reject():
                try:
                    await api.reject_friend_request(req["id"])
                    page.show_snack_bar(ft.SnackBar(ft.Text("已拒绝")))
                    page.run_task(_load_requests)
                except Exception as ex:
                    page.show_snack_bar(ft.SnackBar(ft.Text(f"失败: {ex}")))
            page.run_task(do_reject)

        return ft.Container(
            ft.Row(
                [
                    ft.CircleAvatar(
                        content=ft.Text(str(display)[0].upper(), weight=ft.FontWeight.BOLD),
                        radius=22,
                    ),
                    ft.Column(
                        [
                            ft.Text(display, weight=ft.FontWeight.BOLD),
                            ft.Row([ft.Text(f"@{uname}", size=12, color=ft.Colors.OUTLINE),
                                    ft.Text("·", color=ft.Colors.OUTLINE, size=12),
                                    ft.Text(created, size=12, color=ft.Colors.OUTLINE)],
                                    spacing=4),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.FilledButton("接受", on_click=on_accept),
                    ft.OutlinedButton("拒绝", on_click=on_reject),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            padding=12,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=10,
        )

    body = [
        ft.Row([ft.Text("好友请求", size=18, weight=ft.FontWeight.BOLD), refresh_btn],
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        requests_column,
    ]

    page.run_task(_load_requests)
    return layout(page, api, title="", content=body)
