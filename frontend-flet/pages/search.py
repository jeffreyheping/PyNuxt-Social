"""用户搜索页面

替代: frontend/pages/search.html + components/search_results.html
"""
from __future__ import annotations

import flet as ft
from components.layout import layout, empty_state, spinner
from components.user_card import user_card


def render_search(page: ft.Page, api) -> ft.Control:
    if not api.is_logged_in:
        page.go("/login")
        return ft.Column([])

    search_input = ft.TextField(
        hint_text="搜索用户（用户名 / 昵称）",
        expand=True,
        on_submit=lambda e: _do_search(),
        autofocus=True,
    )
    search_btn = ft.FilledButton("搜索", icon=ft.Icons.SEARCH, on_click=lambda e: _do_search())
    results_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    results_column.controls = [empty_state("输入关键词搜索用户")]

    async def _do_search_async():
        q = search_input.value.strip() if search_input.value else ""
        if not q:
            results_column.controls = [empty_state("输入关键词搜索用户")]
            results_column.update()
            return
        results_column.controls = [spinner("搜索中...")]
        results_column.update()
        try:
            users = await api.search_users(q)
            if not users:
                results_column.controls = [empty_state(f"未找到匹配 '{q}' 的用户")]
            else:
                cards = [user_card(u, api, show_friend_button=True) for u in users]
                # 异步加载每个卡片的好友状态
                results_column.controls = cards
                results_column.update()
                # 逐个异步拉取每个卡片的好友状态
                for card in cards:
                    load_fn = (card.data or {}).get("load_status")
                    if load_fn:
                        try:
                            await load_fn()
                        except Exception:
                            pass
        except Exception as ex:
            results_column.controls = [
                ft.Row([ft.Text(f"搜索失败: {ex}", color=ft.Colors.ERROR)],
                       alignment=ft.MainAxisAlignment.CENTER)
            ]
        results_column.update()

    def _do_search():
        page.run_task(_do_search_async)

    body = [
        ft.Row([search_input, search_btn], spacing=8),
        results_column,
    ]

    return layout(page, api, title="用户搜索", content=body)
