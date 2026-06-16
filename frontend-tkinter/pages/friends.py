"""好友请求页面"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading


class FriendsFrame(ttk.Frame):
    """好友请求列表"""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="好友请求", font=("Arial", 18, "bold")).pack(pady=10)

        ttk.Button(self, text="刷新", command=self.load_requests).pack(pady=5)

        self.requests_frame = ttk.Frame(self)
        self.requests_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.load_requests()

    def load_requests(self):
        for w in self.requests_frame.winfo_children():
            w.destroy()
        ttk.Label(self.requests_frame, text="加载中...").pack(pady=10)

        def _load():
            try:
                requests = self.app.api.get_friend_requests()
                self.after(0, lambda: self._render(requests))
            except Exception as e:
                self.after(0, lambda e=e: messagebox.showerror("加载失败", str(e)))

        threading.Thread(target=_load, daemon=True).start()

    def _render(self, requests):
        for w in self.requests_frame.winfo_children():
            w.destroy()

        if not requests:
            ttk.Label(self.requests_frame, text="暂无好友请求").pack(pady=10)
            return

        for req in requests:
            self._add_request_card(req)

    def _add_request_card(self, req):
        card = ttk.LabelFrame(self.requests_frame)
        card.pack(fill=tk.X, pady=5)

        from_user = req.get("from_user", {}) or {}
        username = from_user.get("username", "未知")
        display = from_user.get("display_name") or username

        ttk.Label(card, text=display, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Label(card, text=f"@{username}", foreground="gray").pack(side=tk.LEFT, padx=5)

        ttk.Button(card, text="接受",
                   command=lambda: self._respond(req["id"], "accept")).pack(side=tk.RIGHT, padx=5)
        ttk.Button(card, text="拒绝",
                   command=lambda: self._respond(req["id"], "reject")).pack(side=tk.RIGHT, padx=5)

    def _respond(self, request_id, action):
        def _do():
            try:
                if action == "accept":
                    self.app.api.accept_friend_request(request_id)
                else:
                    self.app.api.reject_friend_request(request_id)
                self.load_requests()
            except Exception as e:
                messagebox.showerror("操作失败", str(e))
        threading.Thread(target=_do, daemon=True).start()