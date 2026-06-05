"""请求级上下文 — 用 contextvars 替代 clone 模式

每个 HTTP 请求自动获得独立的上下文（ASGI per-request Task 隔离），
BFF 方法通过 self.auth_token / self.current_user_id 访问，
底层自动从 contextvars 读取，零侵入。

v0.5.0 新增。
"""

from contextvars import ContextVar

# 当前请求的认证 Token（由 _build_handler 在请求开始时设置）
_request_token: ContextVar[str | None] = ContextVar('_request_token', default=None)

# 当前请求的用户 ID（由 _build_handler 在请求开始时设置）
_request_user_id: ContextVar[int | None] = ContextVar('_request_user_id', default=None)

# 用户信息缓存（防止同一请求多次查询 /api/auth/me）
_UNSET = object()
_user_cache: ContextVar = ContextVar('_user_cache', default=_UNSET)
