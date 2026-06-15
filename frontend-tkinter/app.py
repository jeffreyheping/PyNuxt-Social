"""主窗口类 — Tkinter 的标准做法"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading

from api import ApiClient
from pages import HomeFrame, LoginFrame, RegisterFrame, FeedFrame, SearchFrame, ProfileFrame, FriendsFrame


class App(tk.Tk):
    """主窗口 — Tkinter 的标准做法

    - 继承 tk.Tk
    - 导航栏 + 页面容器
    - Frame 切换实现页面跳转
    """

    def __init__(self):
        super().__init__()
        self.title("PyNuxt-Social (Tkinter)")
        self.geometry("600x500")
        self.api = ApiClient()

        # 导航栏
        self.nav_frame = ttk.Frame(self)
        self.nav_frame.pack(fill=tk.X)

        # 页面容器
        self.container = ttk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True)

        # 创建所有页面
        self.frames = {}
        for F in (HomeFrame, LoginFrame, RegisterFrame, FeedFrame, SearchFrame, ProfileFrame, FriendsFrame):
            frame = F(self.container, self)
            self.frames[F.__name__.replace("Frame", "").lower()] = frame
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.update_nav()
        self.show_frame("home")

    def update_nav(self):
        """更新导航栏"""
        for w in self.nav_frame.winfo_children():
            w.destroy()

        ttk.Button(self.nav_frame, text="首页", command=lambda: self.show_frame("home")).pack(side=tk.LEFT, padx=5)

        if self.api.is_logged_in:
            ttk.Button(self.nav_frame, text="动态", command=lambda: self.show_frame("feed")).pack(side=tk.LEFT, padx=5)
            ttk.Button(self.nav_frame, text="搜索", command=lambda: self.show_frame("search")).pack(side=tk.LEFT, padx=5)
            ttk.Button(self.nav_frame, text="好友", command=lambda: self.show_frame("friends")).pack(side=tk.LEFT, padx=5)

            user = self.api.current_user or {}
            username = user.get("username", "用户")
            ttk.Label(self.nav_frame, text=username).pack(side=tk.RIGHT, padx=5)
            ttk.Button(self.nav_frame, text="退出", command=self.do_logout).pack(side=tk.RIGHT, padx=5)
        else:
            ttk.Button(self.nav_frame, text="登录", command=lambda: self.show_frame("login")).pack(side=tk.RIGHT, padx=5)
            ttk.Button(self.nav_frame, text="注册", command=lambda: self.show_frame("register")).pack(side=tk.RIGHT, padx=5)

    def show_frame(self, name):
        """切换页面"""
        if not self.api.is_logged_in and name in ("feed", "search", "friends"):
            messagebox.showinfo("提示", "请先登录")
            self.show_frame("login")
            return

        frame = self.frames.get(name)
        if frame:
            frame.tkraise()

    def show_profile(self, username):
        """显示用户主页"""
        profile_frame = self.frames.get("profile")
        if profile_frame:
            profile_frame.load(username)
            profile_frame.tkraise()

    def do_logout(self):
        def _logout():
            try:
                self.api.logout()
            except:
                pass
            self.after(0, lambda: (self.update_nav(), self.show_frame("home")))
        threading.Thread(target=_logout, daemon=True).start()