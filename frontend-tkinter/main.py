"""Tkinter 前端 — PyNuxt-Social

Tkinter 的主流做法：
- 主窗口类继承 tk.Tk
- 每个页面是一个 Frame 类
- 页面切换通过 raise_frame() 实现
- 使用 ttk 控件获得更好的外观
"""
import tkinter as tk
from tkinter import ttk, messagebox
import httpx
import threading

API_BASE = "http://localhost:8000"


class ApiClient:
    """API 客户端 — 同步版本（Tkinter 主线程不能用 async）"""

    def __init__(self):
        self.token = None
        self.current_user = None

    @property
    def is_logged_in(self):
        return self.token is not None

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _get(self, path, params=None):
        resp = httpx.get(f"{API_BASE}{path}", params=params, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path, data=None):
        resp = httpx.post(f"{API_BASE}{path}", json=data, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _put(self, path, data=None):
        resp = httpx.put(f"{API_BASE}{path}", json=data, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    # 认证
    def login(self, username, password):
        result = self._post("/api/auth/login", {"username": username, "password": password})
        self.token = result.get("access_token")
        self.current_user = result.get("user")
        return result

    def register(self, username, email, password, display_name=""):
        data = {"username": username, "email": email, "password": password}
        if display_name:
            data["display_name"] = display_name
        result = self._post("/api/auth/register", data)
        self.token = result.get("access_token")
        self.current_user = result.get("user")
        return result

    def logout(self):
        self._post("/api/auth/logout", {})
        self.token = None
        self.current_user = None

    def fetch_me(self):
        if not self.token:
            return None
        try:
            return self._get("/api/auth/me")
        except:
            return None

    # 帖子
    def get_posts(self, feed="global"):
        return self._get("/api/posts", {"feed": feed})

    def create_post(self, content):
        return self._post("/api/posts", {"content": content})

    def toggle_like(self, post_id):
        return self._post(f"/api/posts/{post_id}/like", {})

    # 用户
    def search_users(self, q):
        return self._get("/api/users", {"q": q})

    def get_user_profile(self, username):
        return self._get(f"/api/users/{username}")

    def get_user_posts(self, username):
        return self._get(f"/api/users/{username}/posts")

    def get_followers(self, username):
        return self._get(f"/api/users/{username}/followers")

    def get_following(self, username):
        return self._get(f"/api/users/{username}/following")

    # 好友
    def get_friend_requests(self):
        return self._get("/api/friends/requests")

    def send_friend_request(self, username):
        return self._post(f"/api/friends/requests/{username}", {})

    def accept_friend_request(self, request_id):
        return self._put(f"/api/friends/requests/{request_id}", {"action": "accept"})

    def reject_friend_request(self, request_id):
        return self._put(f"/api/friends/requests/{request_id}", {"action": "reject"})

    def get_friend_status(self, username):
        return self._get(f"/api/friends/status/{username}")


# ─────────────────────────────────────────────────────────────
# 页面 Frame 类
# ─────────────────────────────────────────────────────────────

class HomeFrame(ttk.Frame):
    """首页"""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.create_widgets()

    def create_widgets(self):
        # 标题
        ttk.Label(self, text="PyNuxt-Social", font=("Arial", 24, "bold")).pack(pady=20)
        ttk.Label(self, text="轻量级社交平台", font=("Arial", 12)).pack(pady=5)

        # 按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=30)

        ttk.Button(btn_frame, text="进入动态流", command=lambda: self.app.show_frame("feed")).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="登录", command=lambda: self.app.show_frame("login")).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="注册", command=lambda: self.app.show_frame("register")).pack(side=tk.LEFT, padx=10)


class LoginFrame(ttk.Frame):
    """登录页"""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="登录", font=("Arial", 18, "bold")).pack(pady=20)

        # 表单
        form = ttk.Frame(self)
        form.pack(pady=10)

        ttk.Label(form, text="用户名:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.username_entry = ttk.Entry(form, width=30)
        self.username_entry.grid(row=0, column=1, pady=5)

        ttk.Label(form, text="密码:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(form, width=30, show="*")
        self.password_entry.grid(row=1, column=1, pady=5)

        # 按钮
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


class FeedFrame(ttk.Frame):
    """动态流"""

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

        # 帖子列表
        self.posts_frame = ttk.Frame(self)
        self.posts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.load_posts()

    def switch_feed(self, feed_type):
        self.feed_type = feed_type
        self.load_posts()

    def load_posts(self):
        # 清空旧内容
        for w in self.posts_frame.winfo_children():
            w.destroy()

        ttk.Label(self.posts_frame, text="加载中...").pack(pady=20)

        def _load():
            try:
                posts = self.app.api.get_posts(self.feed_type)
                self.after(0, lambda: self._render_posts(posts))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("加载失败", str(e)))

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

        like_btn = ttk.Button(card, text=f"❤ {like_count}" if liked else f"♡ {like_count}",
                              command=lambda: self.toggle_like(post["id"]))
        like_btn.pack(anchor=tk.E, padx=5, pady=2)

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
                self.after(0, lambda: messagebox.showerror("搜索失败", str(e)))

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


class ProfileFrame(ttk.Frame):
    """用户主页"""

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
                self.after(0, lambda: messagebox.showerror("加载失败", str(e)))

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


class FriendsFrame(ttk.Frame):
    """好友请求"""

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
                self.after(0, lambda: messagebox.showerror("加载失败", str(e)))

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


# ─────────────────────────────────────────────────────────────
# 主应用类
# ─────────────────────────────────────────────────────────────

class App(tk.Tk):
    """主窗口 — Tkinter 的标准做法"""

    def __init__(self):
        super().__init__()
        self.title("PyNuxt-Social (Tkinter)")
        self.geometry("600x500")
        self.api = ApiClient()

        # 导航栏
        self.nav_frame = ttk.Frame(self)
        self.nav_frame.pack(fill=tk.X)

        self.nav_buttons = {}

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
        """切换页面 — Tkinter 的标准做法"""
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
            self.after(0, lambda: (
                self.update_nav(),
                self.show_frame("home")
            ))
        threading.Thread(target=_logout, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()