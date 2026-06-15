"""动态流页面

替代: frontend/pages/feed.html + components/post_list.html + feed_content.html

功能:
1. Tab 切换「全部动态 / 关注的人」
2. 发帖输入框 + 发布按钮
3. 帖子列表（每个帖子带点赞按钮）
"""
from __future__ import annotations

import flet as ft
from components.layout import layout, spinner, empty_state
from components.post_card import post_card


def render_feed(page: ft.Page, api) -> ft.Control:
    if not api.is_logged_in:
        page.go("/login")
        return ft.Column([])

    # 当前 Tab 状态（global / following）
    current_feed = {"value": "global"}

    # 发帖输入框
    new_post_input = ft.TextField(
        hint_text="说点什么...",
        multiline=True,
        max_lines=5,
        expand=True,
        min_lines=2,
    )
    submit_post_btn = ft.FilledButton("发布", on_click=lambda e: _submit_post())

    # 帖子列表容器（支持动态更新）
    posts_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    # feed tabs
    def switch_feed(feed_type: str):
        current_feed["value"] = feed_type
        page.run_task(_load_posts)

    tab_global = ft.TextButton("全部", on_click=lambda e: switch_feed("global"))
    tab_following = ft.TextButton("关注", on_click=lambda e: switch_feed("following"))

    # --- 加载帖子列表 ---
    async def _load_posts():
        posts_column.controls = [spinner("加载帖子...")]
        posts_column.update()
        try:
            posts = await api.get_posts(feed=current_feed["value"])
            if not posts:
                posts_column.controls = [empty_state("还没有帖子，快来发一条吧！")]
            else:
                posts_column.controls = [post_card(p, api) for p in posts]
        except Exception as ex:
            posts_column.controls = [
                ft.Row([ft.Text(f"加载失败: {ex}", color=ft.Colors.ERROR)],
                       alignment=ft.MainAxisAlignment.CENTER)
            ]
        posts_column.update()

    # --- 发帖 ---
    async def _do_submit_post(content: str):
        submit_post_btn.disabled = True
        new_post_input.disabled = True
        new_post_input.update()
        try:
            await api.create_post(content)
            new_post_input.value = ""
            # 刷新列表
            page.run_task(_load_posts)
        except Exception as ex:
            page.show_snack_bar(ft.SnackBar(ft.Text(f"发布失败: {ex}")))
        finally:
            submit_post_btn.disabled = False
            new_post_input.disabled = False
            new_post_input.update()

    def _submit_post():
        content = new_post_input.value.strip() if new_post_input.value else ""
        if not content:
            return
        page.run_task(_do_submit_post, content)

    # --- 页面组装 ---
    top_card = ft.Container(
        ft.Column(
            [
                ft.Row(
                    [new_post_input, submit_post_btn],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            spacing=8,
        ),
        padding=12,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=10,
    )

    tabs_row = ft.Row(
        [
            ft.Text("动态流", size=18, weight=ft.FontWeight.BOLD),
            ft.VerticalDivider(width=16),
            tab_global,
            tab_following,
        ],
        spacing=8,
    )

    body = [
        top_card,
        ft.Divider(height=1),
        tabs_row,
        posts_column,
    ]

    # 首次加载
    page.run_task(_load_posts)

    return layout(page, api, title="", content=body)
