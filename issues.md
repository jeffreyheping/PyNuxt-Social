# PyNuxt-Social 代码审查 Issues

> 审查日期：2026-06-05
> 审查范围：frontend/ + backend/ 核心模块
> 总体评价：架构设计优秀，主要生产障碍为 N+1 查询问题

---

## P0 — 必须修复（影响生产稳定性）

### P0-1: N+1 查询问题

**位置**：[backend/routers/posts.py#L44-65](backend/routers/posts.py#L44-65)

**问题**：`_serialize_post` 每条帖子执行 3 次独立查询，20 条帖子 = 60+ SQL。

```python
def _serialize_post(post: Post, current_user, db):
    like_count = db.query(Like).filter(Like.post_id == post.id).count()       # SQL 1
    liked_by_me = db.query(Like).filter(...).first()                           # SQL 2
    author = db.query(User).filter(User.id == post.author_id).first()           # SQL 3
```

**修复方案**：在 `get_posts` 里批量查询

```python
def get_posts(...):
    posts = db.query(Post).order_by(...).all()

    # 批量查询作者
    author_ids = {p.author_id for p in posts}
    authors = {u.id: u for u in db.query(User).filter(User.id.in_(author_ids)).all()}

    # 批量查询点赞
    post_ids = [p.id for p in posts]
    likes = db.query(Like).filter(Like.post_id.in_(post_ids)).all()

    # 按 post_id 分组
    likes_by_post = {}
    for l in likes:
        likes_by_post.setdefault(l.post_id, []).append(l)

    # 构造响应
    return [_serialize_post_fast(p, authors, likes_by_post, current_user) for p in posts]
```

**影响**：20 条帖子页面加载从 60+ SQL 降至 ~4 SQL。

---

### P0-2: `datetime.utcnow()` 已弃用

**位置**：
- [backend/models.py#L25](backend/models.py#L25) — `User.created_at`
- [backend/models.py#L46](backend/models.py#L46) — `Post.created_at`
- [backend/models.py#L85](backend/models.py#L85) — `FriendRequest.created_at/updated_at`
- [backend/routers/auth.py#L74](backend/routers/auth.py#L74) — JWT 过期时间

**问题**：Python 3.12+ 已弃用 `datetime.utcnow()`，会产生 DeprecationWarning。

**修复方案**：统一改为 `datetime.now(timezone.utc)`

```python
from datetime import datetime, timezone

# models.py
created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# auth.py
expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
```

---

## P1 — 强烈建议修复（影响正确性/安全性）

### P1-1: 公开 API 泄漏用户邮箱

**位置**：[backend/routers/users.py](backend/routers/users.py)

**问题**：`GET /api/users/{username}` 响应包含 `email` 字段，隐私泄漏。

**修复方案**：创建 `UserPublicResponse` 排除 email：

```python
class UserPublicResponse(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    created_at: datetime
    post_count: int
    follower_count: int
    following_count: int
    # email 已移除
```

---

### P1-2: Feed Tab 与发帖表单不同步

**位置**：[frontend/pages/feed.html#L7](frontend/pages/feed.html#L7)

**问题**：发帖表单 hardcode `feed=global`，用户切换到"关注" Tab 后发帖，实际发到全局流。

```html
<form hx-post="/bff/posts?feed=global" ...>
```

**修复方案**：用隐藏字段动态跟随当前 Tab。

---

### P1-3: `_user_cache` 模块级全局变量

**位置**：[frontend/pynuxt/auth.py](frontend/pynuxt/auth.py)

**问题**：`_shared_client` 和 `_user_cache` 是模块级全局变量，多实例部署时可能被共享。

**修复方案**：改为类变量（已有成功案例，见 `BFFBase._shared_client`）。

---

## P2 — 建议修复（影响可维护性）

### P2-1: `create_post` 参数来源不一致

**位置**：[frontend/bff_core.py#L63-66](frontend/bff_core.py#L63-66)

**问题**：`feed` 用 Query 参数，`content` 用 Form 参数，来源不统一。

```python
async def create_post(self, content: str = Form(...), feed: str = Query("global")):
```

**修复方案**：统一为 Form 参数或 Query 参数。

---

### P2-2: followers/following 返回相同数据

**位置**：[backend/routers/users.py](backend/routers/users.py) — `get_followers`/`get_following`

**问题**：好友关系是双向的，两接口查询逻辑相同，返回数据一样。

**说明**：这是设计问题，ARCHITECTURE.md 已有记录（D1）。

---

## P3 — 未来改进（不紧急）

### P3-1: 无分页 UI

**位置**：[frontend/pages/feed.html](frontend/pages/feed.html)

**问题**：API 支持 skip/limit，但前端无"加载更多"按钮。

### P3-2: 无删除/编辑帖子功能

**问题**：用户无法删除自己发的帖子。

### P3-3: BFFBase 克隆模式历史包袱

**位置**：[frontend/pynuxt/bff.py](frontend/pynuxt/bff.py)

**问题**：v0.5.0 已用 contextvars 替代 clone，但 `__init__` 仍接收废弃的 `template_dirs` 参数。

---

## 已确认设计决策（无需修复）

| 项 | 说明 |
|----|------|
| D4 | 无分页 UI — 简化设计 |
| D5 | 无删除帖子 — 社交产品常见 |
| D6 | 无编辑资料 — MVP 范围 |
| D9 | BFFBase 构造函参数无效 — 文档已标注 |
| D10 | `_action_then_refresh` 未被调用 — 计划删除 |
| D11 | httpx client shutdown — lifespan 已修复 |
| D12 | 无 CSRF 防护 — HTMX 表单场景可接受 |

---

## 修复优先级汇总

| 优先级 | Issue | 位置 | 预估工作量 |
|--------|-------|------|----------|
| P0-1 | N+1 查询 | posts.py | 中 |
| P0-2 | datetime.utcnow() | models.py, auth.py | 小 |
| P1-1 | email 泄漏 | users.py | 小 |
| P1-2 | Feed Tab 不同步 | feed.html | 小 |
| P1-3 | 模块级全局变量 | auth.py | 中 |
| P2-1 | 参数来源不一致 | bff_core.py | 小 |
| P2-2 | followers/following | users.py | 小 |
