"""首页 — 未登录用户的着陆页

替代: frontend/pages/index.html
"""
from __future__ import annotations

import flet as ft
from components.layout import layout


def render_home(page: ft.Page, api) -> ft.Control:
    """首页: 欢迎信息 + 进入动态流/登录 的按钮"""
    if api.is_logged_in:
        # 已登录 — 直接展示动态流入口（简化: 直接跳 /feed）
        page.go("/feed")
        return ft.Column([])

    body = ft.Container(
        ft.Column(
            [
                ft.Row(
                    [ft.Text("PyNuxt-Social", size=40, weight=ft.FontWeight.BOLD)],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Row(
                    [ft.Text("轻量级社交平台 — 用 Python + Flet 构建", color=ft.Colors.OUTLINE, size=16)],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=24),
                ft.Row(
                    [
                        ft.FilledButton("进入动态流", on_click=lambda e: e.page.go("/feed"), width=200),
                        ft.OutlinedButton("登录", on_click=lambda e: e.page.go("/login"), width=120),
                        ft.OutlinedButton("注册", on_click=lambda e: e.page.go("/register"), width=120),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=12,
                ),
                ft.Container(height=32),
                ft.Row(
                    [
                        ft.Icon(ft.Icons.ARTICLE, size=32, color=ft.Colors.PRIMARY),
                        ft.Text("发布动态", size=16),
                        ft.VerticalDivider(width=32),
                        ft.Icon(ft.Icons.SEARCH, size=32, color=ft.Colors.PRIMARY),
                        ft.Text("搜索用户", size=16),
                        ft.VerticalDivider(width=32),
                        ft.Icon(ft.Icons.GROUP, size=32, color=ft.Colors.PRIMARY),
                        ft.Text("添加好友", size=16),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8,
                ),
            ],
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        expand=True,
        alignment=ft.Alignment(0, -0.3),
    )

    return layout(page, api, title="", content=body)
