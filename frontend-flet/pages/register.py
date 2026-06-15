"""注册页

替代: frontend/pages/register.html
"""
from __future__ import annotations

import flet as ft
from components.layout import layout


def render_register(page: ft.Page, api) -> ft.Control:
    username = ft.TextField(label="用户名", width=360, autofocus=True, on_submit=lambda e: _submit())
    email = ft.TextField(label="邮箱", width=360, on_submit=lambda e: _submit())
    display_name = ft.TextField(label="昵称（可选）", width=360, on_submit=lambda e: _submit())
    password = ft.TextField(label="密码（至少6位）", password=True, can_reveal_password=True, width=360, on_submit=lambda e: _submit())
    error_msg = ft.Text("", color=ft.Colors.ERROR, visible=False)
    submit_btn = ft.FilledButton("注册", width=360, on_click=lambda e: _submit())

    def _submit():
        u = username.value.strip() if username.value else ""
        e = email.value.strip() if email.value else ""
        d = display_name.value.strip() if display_name.value else ""
        p = password.value or ""
        if not u or not e or not p:
            error_msg.value = "用户名、邮箱和密码都是必填项"
            error_msg.visible = True
            error_msg.update()
            return
        if len(p) < 6:
            error_msg.value = "密码至少6位"
            error_msg.visible = True
            error_msg.update()
            return

        submit_btn.disabled = True
        submit_btn.text = "注册中..."
        submit_btn.update()

        async def do_register():
            try:
                result = await api.register(u, e, p, d)
                token = result.get("access_token")
                if not token:
                    raise RuntimeError("注册成功但未返回 token")
                api.token = token
                api.current_user = result.get("user")
                page.go("/feed")
            except Exception as ex:
                error_msg.value = f"注册失败: {ex}"
                error_msg.visible = True
                error_msg.update()
            finally:
                submit_btn.disabled = False
                submit_btn.text = "注册"
                if submit_btn.page:
                    submit_btn.update()

        page.run_task(do_register)

    card = ft.Container(
        ft.Column(
            [
                ft.Text("注册", size=24, weight=ft.FontWeight.BOLD),
                username,
                email,
                display_name,
                password,
                error_msg,
                submit_btn,
                ft.Divider(),
                ft.Row(
                    [
                        ft.Text("已有账号？"),
                        ft.TextButton("去登录", on_click=lambda e: e.page.go("/login")),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=4,
                ),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=24,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=12,
        width=420,
    )

    centered = ft.Row([card], alignment=ft.MainAxisAlignment.CENTER, expand=True)
    body = ft.Container(centered, expand=True, alignment=ft.Alignment(0, -0.1))
    return layout(page, api, title="", content=body)
