"""API 服务层 — 门面类

一个 ApiClient 实例 = 一个 Flet 会话。token 存在实例里。

拆分策略:
    - _base.py   → HTTP 基础能力（连接、通用方法、token）
    - _auth.py   → AuthMixin（login / register / logout / fetch_me）
    - _post.py   → PostMixin（get_posts / create_post / toggle_like）
    - _user.py   → UserMixin（search / profile / followers / following）
    - _friend.py → FriendMixin（requests / send / accept / reject / status）
    - api.py     → 门面类，组合全部 Mixin

对外接口不变：from services.api import ApiClient
"""
from __future__ import annotations

from services._base import ApiBase
from services._auth import AuthMixin
from services._post import PostMixin
from services._user import UserMixin
from services._friend import FriendMixin


class ApiClient(AuthMixin, PostMixin, UserMixin, FriendMixin):
    """封装对 FastAPI 后端的所有 REST API 调用

    按 MRO 顺序：AuthMixin → PostMixin → UserMixin → FriendMixin → ApiBase
    所有 Mixin 继承 ApiBase，仅 ApiBase.__init__ 生效（Python MRO 保证）。
    """
    pass
