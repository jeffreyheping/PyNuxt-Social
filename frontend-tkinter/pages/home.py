"""首页"""
import tkinter as tk
from tkinter import ttk


class HomeFrame(ttk.Frame):
    """首页 — 欢迎信息和入口按钮"""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="PyNuxt-Social", font=("Arial", 24, "bold")).pack(pady=20)
        ttk.Label(self, text="轻量级社交平台", font=("Arial", 12)).pack(pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=30)

        ttk.Button(btn_frame, text="进入动态流", command=lambda: self.app.show_frame("feed")).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="登录", command=lambda: self.app.show_frame("login")).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="注册", command=lambda: self.app.show_frame("register")).pack(side=tk.LEFT, padx=10)