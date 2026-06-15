"""通用布局组件 — 导航栏 + 内容区

替代原 frontend/layouts/default.html 的作用。

用法:
    @component
    def my_page():
        return layout(title="我的页面", content=[ft.Text("hi")])
"""
from __future__ import annotations

import flet as ft


def _nav_links(api) -> list[ft.Control]:
    """根据登录状态生成导航链接

    对应原 Jinja2 {% if current_user %}...{% endif %} 的条件渲染
    """
    links: list[ft.Control] = []
    if api and api.is_logged_in:
        links.append(ft.TextButton("动态", on_click=lambda e: e.page.go("/feed")))
        links.append(ft.TextButton("搜索", on_click=lambda e: e.page.go("/search")))
        links.append(ft.TextButton("好友", on_click=lambda e: e.page.go("/friends")))
    return links


def _auth_area(api) -> ft.Control:
    """登录状态区域: 未登录显示「登录/注册」，已登录显示用户名+登出"""
    if not api or not api.is_logged_in:
        return ft.Row([
            ft.TextButton("登录", on_click=lambda e: e.page.go("/login")),
            ft.TextButton("注册", on_click=lambda e: e.page.go("/register")),
        ], spacing=4)

    user = api.current_user or {}
    username = user.get("username", user.get("display_name", "用户"))
    display = ft.Text(username, weight=ft.FontWeight.BOLD)

    def go_profile(e):
        e.page.go(f"/users/{username}")

    def do_logout(e):
        # Flet 1.0 风格：同步操作 + page.go
        api.token = None
        api.current_user = None
        e.page.go("/")

    return ft.Row([
        ft.TextButton("退出登录", on_click=do_logout),
        display,
    ], spacing=8)


def layout(
    page: ft.Page,
    api,
    title: str,
    content: ft.Control | list[ft.Control],
) -> ft.Column:
    """标准页面布局 — 顶部导航 + 内容区

    Args:
        page: 当前 Page（用于读取 session 级状态）
        api: ApiClient 实例（用于判断登录状态）
        title: 页面标题（显示在页面顶部）
        content: 页面主体内容，可以是单个 Control 或 Control 列表
    """
    # 导航栏
    brand = ft.TextButton(
        "PyNuxt-Social",
        style=ft.ButtonStyle(
            text_style=ft.TextStyle(size=18, weight=ft.FontWeight.BOLD)
        ),
        on_click=lambda e: e.page.go("/"),
    )
    nav = ft.Row(
        [
            brand,
            ft.Row(_nav_links(api), spacing=4),
            ft.Row([_auth_area(api)], expand=True, alignment=ft.MainAxisAlignment.END),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        spacing=16,
    )

    divider = ft.Divider(height=1)

    title_text = ft.Text(title, size=28, weight=ft.FontWeight.BOLD)
    title_row = ft.Row([title_text], alignment=ft.MainAxisAlignment.CENTER)

    # 内容区 — 支持单个控件或列表
    if isinstance(content, list):
        body = ft.Column(content, expand=True, spacing=16, scroll=ft.ScrollMode.AUTO)
    else:
        body = content

    return ft.Column(
        [
            ft.Container(nav, padding=ft.Padding(16, 8, 16, 8)),
            divider,
            ft.Container(
                ft.Column([title_row, body], expand=True, spacing=16),
                padding=ft.Padding(16, 16, 16, 16),
                expand=True,
            ),
        ],
        expand=True,
        spacing=0,
    )


def message(text: str, color: str = ft.Colors.ON_SURFACE, size: int = 16) -> ft.Text:
    """便捷的纯文本占位控件"""
    return ft.Text(text, size=size, color=color)


def spinner(label: str = "加载中...") -> ft.Row:
    """居中的加载指示"""
    return ft.Row(
        [ft.ProgressRing(width=24, height=24, stroke_width=2), ft.Text(label)],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=12,
    )


def error_box(text: str) -> ft.Container:
    """红色背景的错误提示框"""
    return ft.Container(
        ft.Row([ft.Icon(ft.Icons.ERROR, color=ft.Colors.ON_ERROR_CONTAINER), ft.Text(text)]),
        bgcolor=ft.Colors.ERROR_CONTAINER,
        padding=ft.Padding(12, 8, 12, 8),
        border_radius=8,
        expand=True,
    )


def empty_state(text: str) -> ft.Container:
    """空状态提示"""
    return ft.Container(
        ft.Column(
            [
                ft.Icon(ft.Icons.INBOX, size=64, color=ft.Colors.OUTLINE),
                ft.Text(text, color=ft.Colors.OUTLINE, size=16),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
        padding=40,
        expand=True,
    )


def avatar(user: dict, size: int = 40) -> ft.CircleAvatar:
    """用户头像 — 用首字母做占位图（与原版 HTMX 的头像卡片同理）"""
    name = user.get("display_name") or user.get("username") or "?"
    letter = str(name)[0].upper()
    return ft.CircleAvatar(content=ft.Text(letter, weight=ft.FontWeight.BOLD), radius=size / 2)
