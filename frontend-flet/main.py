"""Flet 前端入口

用法:
    flet run main.py
    # 或
    python main.py

路由表（模仿 Nuxt 的 filesytem routing，但显式注册）:
    /              → 首页
    /login         → 登录
    /register      → 注册
    /feed          → 动态流（需登录）
    /search        → 用户搜索（需登录）
    /friends       → 好友请求（需登录）
    /users/{username} → 用户主页

架构:
    - 每个 Session 有一个独立的 ApiClient（同一浏览器 tab 内共享状态）
    - 页面函数 (render_xxx) 返回一个 Flet 控件树
    - 通过 update_title 触发路由重绘
"""
from __future__ import annotations

import flet as ft

from services.api import ApiClient

from pages.home import render_home
from pages.login import render_login
from pages.register import render_register
from pages.feed import render_feed
from pages.search import render_search
from pages.profile import render_profile
from pages.friends import render_friends


TOKEN_KEY = "auth_token"
USER_KEY = "current_user"


async def main(page: ft.Page):
    page.title = "PyNuxt-Social"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 0
    page.spacing = 0

    # 每个 session 一个 ApiClient
    api = ApiClient()

    # 从 client_storage 恢复 token（跨刷新保留登录）
    try:
        token = page.client_storage.get(TOKEN_KEY)
        if token:
            api.token = token
            api.current_user = page.client_storage.get(USER_KEY)
    except Exception:
        pass

    # 页面容器 — 内容会被 route_change 替换
    body = ft.Column([], expand=True, spacing=0, scroll=ft.ScrollMode.AUTO)

    async def route_change(route: ft.RouteChangeEvent):
        """路由切换逻辑

        注意: 每个页面返回一个全新的 Control 树，替换 body 的内容。
        """
        body.controls = []

        path = route.route or "/"
        # 解析动态路由 /users/{username}
        if path.startswith("/users/"):
            username = path[len("/users/"):].strip("/")
            ctrl = render_profile(page, api, username)
        elif path == "/feed":
            ctrl = render_feed(page, api)
        elif path == "/search":
            ctrl = render_search(page, api)
        elif path == "/friends":
            ctrl = render_friends(page, api)
        elif path == "/login":
            ctrl = render_login(page, api)
        elif path == "/register":
            ctrl = render_register(page, api)
        elif path == "/" or path == "":
            ctrl = render_home(page, api)
        else:
            ctrl = ft.Container(ft.Text(f"404: 找不到页面 {path}"), padding=40)

        body.controls = [ctrl]
        page.update()

        # 登录状态变化后持久化（页面切换时顺带保存）
        try:
            if api.token:
                page.client_storage.set(TOKEN_KEY, api.token)
                if api.current_user:
                    page.client_storage.set(USER_KEY, api.current_user)
            else:
                page.client_storage.remove(TOKEN_KEY)
                page.client_storage.remove(USER_KEY)
        except Exception:
            pass

    async def view_pop(e: ft.ViewPopEvent):
        # 支持浏览器的返回键
        if page.views:
            page.views.pop()
        page.update()

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    # 初始路由
    initial_route = page.route or "/"
    page.route = initial_route

    # 给 body 一个初始占位内容，等 route_change 再填充
    page.add(body)
    await route_change(ft.RouteChangeEvent(route=initial_route))


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP)
