"""API 客户端 — 同步版本（Tkinter 主线程不能用 async）"""
import httpx

API_BASE = "http://localhost:8000"


class ApiClient:
    """封装对 FastAPI 后端的所有 REST API 调用"""

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