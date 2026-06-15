"""注册页"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading


class RegisterFrame(ttk.Frame):
    """注册页"""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="注册", font=("Arial", 18, "bold")).pack(pady=20)

        form = ttk.Frame(self)
        form.pack(pady=10)

        ttk.Label(form, text="用户名:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.username_entry = ttk.Entry(form, width=30)
        self.username_entry.grid(row=0, column=1, pady=5)

        ttk.Label(form, text="邮箱:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.email_entry = ttk.Entry(form, width=30)
        self.email_entry.grid(row=1, column=1, pady=5)

        ttk.Label(form, text="昵称(可选):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.display_entry = ttk.Entry(form, width=30)
        self.display_entry.grid(row=2, column=1, pady=5)

        ttk.Label(form, text="密码:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(form, width=30, show="*")
        self.password_entry.grid(row=3, column=1, pady=5)

        ttk.Button(self, text="注册", command=self.do_register).pack(pady=10)
        ttk.Button(self, text="返回首页", command=lambda: self.app.show_frame("home")).pack(pady=5)

    def do_register(self):
        username = self.username_entry.get().strip()
        email = self.email_entry.get().strip()
        display = self.display_entry.get().strip()
        password = self.password_entry.get()

        if not username or not email or not password:
            messagebox.showerror("错误", "用户名、邮箱、密码必填")
            return

        def _register():
            try:
                self.app.api.register(username, email, password, display)
                self.app.update_nav()
                self.app.show_frame("feed")
            except Exception as e:
                messagebox.showerror("注册失败", str(e))

        threading.Thread(target=_register, daemon=True).start()