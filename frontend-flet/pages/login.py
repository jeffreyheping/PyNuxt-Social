"""登录页

替代: frontend/pages/login.html
"""
from __future__ import annotations

import flet as ft
from components.layout import layout


def render_login(page: ft.Page, api) -> ft.Control:
    username = ft.TextField(label="用户名", width=360, autofocus=True, on_submit=lambda e: _submit())
    password = ft.TextField(label="密码", password=True, can_reveal_password=True, width=360, on_submit=lambda e: _submit())
    error_msg = ft.Text("", color=ft.Colors.ERROR, visible=False)
    submit_btn = ft.FilledButton("登录", width=360, on_click=lambda e: _submit())

    def _submit():
        uname = username.value.strip() if username.value else ""
        pwd = password.value or ""
        if not uname or not pwd:
            error_msg.value = "请输入用户名和密码"
            error_msg.visible = True
            error_msg.update()
            return

        submit_btn.disabled = True
        submit_btn.text = "登录中..."
        submit_btn.update()

        async def do_login():
            try:
                result = await api.login(uname, pwd)
                token = result.get("access_token")
                if not token:
                    raise RuntimeError("后端未返回 token")
                api.token = token
                api.current_user = result.get("user")
                page.go("/feed")
            except Exception as ex:
                error_msg.value = f"登录失败: {ex}"
                error_msg.visible = True
                error_msg.update()
            finally:
                submit_btn.disabled = False
                submit_btn.text = "登录"
                if submit_btn.page:
                    submit_btn.update()

        page.run_task(do_login)

    card = ft.Container(
        ft.Column(
            [
                ft.Text("登录", size=24, weight=ft.FontWeight.BOLD),
                username,
                password,
                error_msg,
                submit_btn,
                ft.Divider(),
                ft.Row(
                    [
                        ft.Text("还没有账号？"),
                        ft.TextButton("去注册", on_click=lambda e: e.page.go("/register")),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=4,
                ),
            ],
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=24,
        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=12,
        width=420,
    )

    centered = ft.Row([card], alignment=ft.MainAxisAlignment.CENTER, expand=True)
    body = ft.Container(centered, expand=True, alignment=ft.Alignment(0, -0.2))

    return layout(page, api, title="", content=body)
