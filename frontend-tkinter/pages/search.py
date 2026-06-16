"""用户搜索页面"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading


class SearchFrame(ttk.Frame):
    """用户搜索"""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="搜索用户", font=("Arial", 18, "bold")).pack(pady=10)

        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, padx=10, pady=10)

        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<Return>", lambda e: self.do_search())

        ttk.Button(search_frame, text="搜索", command=self.do_search).pack(side=tk.LEFT, padx=5)

        self.results_frame = ttk.Frame(self)
        self.results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def do_search(self):
        q = self.search_entry.get().strip()
        if not q:
            return

        for w in self.results_frame.winfo_children():
            w.destroy()
        ttk.Label(self.results_frame, text="搜索中...").pack(pady=10)

        def _search():
            try:
                users = self.app.api.search_users(q)
                self.after(0, lambda: self._render_results(users))
            except Exception as e:
                self.after(0, lambda e=e: messagebox.showerror("搜索失败", str(e)))

        threading.Thread(target=_search, daemon=True).start()

    def _render_results(self, users):
        for w in self.results_frame.winfo_children():
            w.destroy()

        if not users:
            ttk.Label(self.results_frame, text="未找到用户").pack(pady=10)
            return

        for user in users:
            self._add_user_card(user)

    def _add_user_card(self, user):
        card = ttk.Frame(self.results_frame)
        card.pack(fill=tk.X, pady=5)

        username = user.get("username", "")
        display = user.get("display_name") or username

        ttk.Label(card, text=display, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Label(card, text=f"@{username}", foreground="gray").pack(side=tk.LEFT, padx=5)

        ttk.Button(card, text="查看主页",
                   command=lambda: self.app.show_profile(username)).pack(side=tk.RIGHT, padx=5)