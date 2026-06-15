"""登录页"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading


class LoginFrame(ttk.Frame):
    """登录页"""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="登录", font=("Arial", 18, "bold")).pack(pady=20)

        form = ttk.Frame(self)
        form.pack(pady=10)

        ttk.Label(form, text="用户名:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.username_entry = ttk.Entry(form, width=30)
        self.username_entry.grid(row=0, column=1, pady=5)

        ttk.Label(form, text="密码:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(form, width=30, show="*")
        self.password_entry.grid(row=1, column=1, pady=5)

        ttk.Button(self, text="登录", command=self.do_login).pack(pady=10)
        ttk.Button(self, text="返回首页", command=lambda: self.app.show_frame("home")).pack(pady=5)

    def do_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showerror("错误", "请输入用户名和密码")
            return

        def _login():
            try:
                self.app.api.login(username, password)
                self.app.update_nav()
                self.app.show_frame("feed")
            except Exception as e:
                messagebox.showerror("登录失败", str(e))

        threading.Thread(target=_login, daemon=True).start()