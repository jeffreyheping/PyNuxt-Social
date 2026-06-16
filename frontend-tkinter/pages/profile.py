"""用户主页"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading


class ProfileFrame(ttk.Frame):
    """用户主页 — 用户信息 + 帖子列表 + 好友按钮"""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.username = None
        self.create_widgets()

    def create_widgets(self):
        self.header_frame = ttk.Frame(self)
        self.header_frame.pack(fill=tk.X, padx=10, pady=10)

        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10)

    def load(self, username):
        self.username = username
        for w in self.header_frame.winfo_children():
            w.destroy()
        for w in self.content_frame.winfo_children():
            w.destroy()

        ttk.Label(self.header_frame, text="加载中...").pack(pady=10)

        def _load():
            try:
                profile = self.app.api.get_user_profile(username)
                posts = self.app.api.get_user_posts(username)
                self.after(0, lambda: self._render(profile, posts))
            except Exception as e:
                self.after(0, lambda e=e: messagebox.showerror("加载失败", str(e)))

        threading.Thread(target=_load, daemon=True).start()

    def _render(self, profile, posts):
        for w in self.header_frame.winfo_children():
            w.destroy()

        display = profile.get("display_name") or self.username
        post_count = profile.get("post_count", 0)
        follower_count = profile.get("follower_count", 0)
        following_count = profile.get("following_count", 0)

        ttk.Label(self.header_frame, text=display, font=("Arial", 18, "bold")).pack(anchor=tk.W)
        ttk.Label(self.header_frame, text=f"@{self.username}", foreground="gray").pack(anchor=tk.W)
        ttk.Label(self.header_frame,
                  text=f"帖子: {post_count}  粉丝: {follower_count}  关注: {following_count}").pack(anchor=tk.W, pady=5)

        # 好友按钮
        if self.app.api.is_logged_in:
            def _check_status():
                try:
                    status = self.app.api.get_friend_status(self.username).get("status", "none")
                    self.after(0, lambda: self._add_friend_btn(status))
                except:
                    pass
            threading.Thread(target=_check_status, daemon=True).start()

        # 帖子列表
        ttk.Label(self.content_frame, text="帖子", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=5)

        posts_frame = ttk.Frame(self.content_frame)
        posts_frame.pack(fill=tk.BOTH, expand=True)

        if not posts:
            ttk.Label(posts_frame, text="暂无帖子").pack(pady=10)
        else:
            for post in posts:
                card = ttk.LabelFrame(posts_frame)
                card.pack(fill=tk.X, pady=5)
                ttk.Label(card, text=post.get("content", ""), wraplength=400).pack(anchor=tk.W, padx=5, pady=5)

    def _add_friend_btn(self, status):
        if status == "self":
            return

        btn_text = {
            "accepted": "已是好友",
            "pending": "已发送请求",
            "pending_received": "接受请求",
            "rejected": "已拒绝",
            "none": "加好友"
        }.get(status, "")

        if status == "pending_received":
            ttk.Button(self.header_frame, text=btn_text,
                       command=self._accept_request).pack(anchor=tk.W, pady=5)
        elif status == "none":
            ttk.Button(self.header_frame, text=btn_text,
                       command=self._send_request).pack(anchor=tk.W, pady=5)
        elif btn_text:
            ttk.Label(self.header_frame, text=btn_text, foreground="gray").pack(anchor=tk.W, pady=5)

    def _send_request(self):
        def _do():
            try:
                self.app.api.send_friend_request(self.username)
                messagebox.showinfo("成功", "已发送好友请求")
                self.load(self.username)
            except Exception as e:
                messagebox.showerror("失败", str(e))
        threading.Thread(target=_do, daemon=True).start()

    def _accept_request(self):
        def _do():
            try:
                requests = self.app.api.get_friend_requests()
                for r in requests:
                    from_user = r.get("from_user", {}) or {}
                    if from_user.get("username") == self.username:
                        self.app.api.accept_friend_request(r["id"])
                        messagebox.showinfo("成功", "已接受好友请求")
                        self.load(self.username)
                        return
                messagebox.showinfo("提示", "请前往好友页面处理")
            except Exception as e:
                messagebox.showerror("失败", str(e))
        threading.Thread(target=_do, daemon=True).start()