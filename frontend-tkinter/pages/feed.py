"""动态流页面"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading


class FeedFrame(ttk.Frame):
    """动态流 — 发帖 + 帖子列表（可滚动）"""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.feed_type = "global"
        self.create_widgets()

    def create_widgets(self):
        # 发帖区
        post_frame = ttk.LabelFrame(self, text="发布新动态")
        post_frame.pack(fill=tk.X, padx=10, pady=10)

        self.post_entry = ttk.Entry(post_frame, width=50)
        self.post_entry.pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(post_frame, text="发布", command=self.do_post).pack(side=tk.LEFT, padx=5)

        # Tab 切换
        tab_frame = ttk.Frame(self)
        tab_frame.pack(fill=tk.X, padx=10)

        ttk.Button(tab_frame, text="全部", command=lambda: self.switch_feed("global")).pack(side=tk.LEFT, padx=5)
        ttk.Button(tab_frame, text="关注", command=lambda: self.switch_feed("following")).pack(side=tk.LEFT, padx=5)

        # 帖子列表 — Canvas + Scrollbar 实现滚动
        list_outer = ttk.Frame(self)
        list_outer.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._canvas = tk.Canvas(list_outer, highlightthickness=0)
        v_scroll = ttk.Scrollbar(list_outer, orient=tk.VERTICAL, command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=v_scroll.set)

        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.posts_frame = ttk.Frame(self._canvas)
        self._canvas_window = self._canvas.create_window((0, 0), window=self.posts_frame, anchor=tk.NW)

        # 帖子 frame 大小变化时更新滚动区域
        self.posts_frame.bind("<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))

        # Canvas 宽度跟随外层
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # 鼠标滚轮
        self._canvas.bind("<Enter>", lambda e: self._bind_mousewheel())
        self._canvas.bind("<Leave>", lambda e: self._unbind_mousewheel())

        self.load_posts()

    def _on_canvas_configure(self, event):
        """Canvas 大小变化时，让内部 frame 宽度跟随"""
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _bind_mousewheel(self):
        """进入区域时绑定鼠标滚轮"""
        self._canvas.bind_all("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def _unbind_mousewheel(self):
        """离开区域时解绑鼠标滚轮"""
        self._canvas.unbind_all("<MouseWheel>")

    def switch_feed(self, feed_type):
        self.feed_type = feed_type
        self.load_posts()

    def load_posts(self):
        for w in self.posts_frame.winfo_children():
            w.destroy()
        ttk.Label(self.posts_frame, text="加载中...").pack(pady=20)

        def _load():
            try:
                posts = self.app.api.get_posts(self.feed_type)
                self.after(0, lambda: self._render_posts(posts))
            except Exception as e:
                self.after(0, lambda e=e: messagebox.showerror("加载失败", str(e)))

        threading.Thread(target=_load, daemon=True).start()

    def _render_posts(self, posts):
        for w in self.posts_frame.winfo_children():
            w.destroy()

        if not posts:
            ttk.Label(self.posts_frame, text="暂无帖子").pack(pady=20)
            return

        for post in posts:
            self._add_post_card(post)

    def _add_post_card(self, post):
        card = ttk.LabelFrame(self.posts_frame)
        card.pack(fill=tk.X, pady=5)

        author = post.get("author", {})
        author_name = author.get("display_name") or author.get("username", "未知")

        ttk.Label(card, text=author_name, font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Label(card, text=post.get("content", ""), wraplength=400).pack(anchor=tk.W, padx=5, pady=2)

        like_count = post.get("like_count", 0)
        liked = post.get("liked_by_me", False)

        ttk.Button(card, text=f"❤ {like_count}" if liked else f"♡ {like_count}",
                   command=lambda: self.toggle_like(post["id"])).pack(anchor=tk.E, padx=5, pady=2)

    def do_post(self):
        content = self.post_entry.get().strip()
        if not content:
            return

        def _post():
            try:
                self.app.api.create_post(content)
                self.post_entry.delete(0, tk.END)
                self.load_posts()
            except Exception as e:
                messagebox.showerror("发布失败", str(e))

        threading.Thread(target=_post, daemon=True).start()

    def toggle_like(self, post_id):
        def _like():
            try:
                self.app.api.toggle_like(post_id)
                self.load_posts()
            except Exception as e:
                messagebox.showerror("操作失败", str(e))

        threading.Thread(target=_like, daemon=True).start()
