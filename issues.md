# PyNuxt-Social 代码审查 & 实施计划

> 审查日期：2026-06-05
> 审查范围：frontend/ + backend/ 核心模块
> 总体评价：架构设计优秀，主要生产障碍为 N+1 查询问题

---

## 一、实施路线图（总览）

按优先级和依赖关系，分成三个阶段实施：

| 阶段 | 目标 | 关键任务 |
|------|------|---------|
| **第一阶段：稳定性** | 修复生产问题，替换不可靠依赖 | N+1 查询、datetime 弃用、配置管理 |
| **第二阶段：体验优化** | 提升开发体验和用户体验 | 引入 Alpine.js、修复 Feed Tab 同步、环境变量 |
| **第三阶段：框架升级** | 参考 FastBlocks 改进框架 | CSRF 中间件、HTMX 响应类、响应压缩 |

---

## 二、问题详情（按优先级）

### P0 — 必须修复（影响生产稳定性）

#### P0-1: N+1 查询问题

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

#### P0-2: `datetime.utcnow()` 已弃用

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

**说明**：
- 后端已使用 `python-jose`（FastAPI 官方推荐方案），无需改动
- 前端并未手写 JWT encode/decode，只是转发 token 给后端验证，无需替换

---
### P1 — 强烈建议修复（影响正确性/安全性/体验）

#### P1-1: 公开 API 泄漏用户邮箱

**位置**：[backend/routers/users.py](backend/routers/users.py)

**问题**：`GET /api/users/{username}` 响应包含 `email` 字段，隐私泄漏。

**修复方案**：创建 `UserPublicResponse` 排除 email

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

#### P1-2: Feed Tab 与发帖表单不同步

**位置**：[frontend/pages/feed.html#L7](frontend/pages/feed.html#L7)

**问题**：发帖表单 hardcode `feed=global`，用户切换到"关注" Tab 后发帖，实际发到全局流。

**修复方案**：结合 Alpine.js 动态同步 Tab 状态

---

#### P1-3: `_user_cache` 模块级全局变量

**位置**：[frontend/pynuxt/auth.py](frontend/pynuxt/auth.py)

**问题**：`_shared_client` 和 `_user_cache` 是模块级全局变量，多实例部署时可能被共享。

**修复方案**：改为类变量（已有成功案例，见 `BFFBase._shared_client`）

---

#### P1-4: 配置管理使用 `os.getenv()` 缺乏类型安全

**位置**：
- [backend/config.py](backend/config.py)
- [frontend/config.py](frontend/config.py)

**问题**：纯 `os.getenv()` 读取环境变量，无类型校验，无 IDE 自动补全。

**修复方案**：使用 `pydantic-settings`（FastAPI 官方推荐）

```bash
pip install pydantic-settings
```

```python
# backend/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    jwt_secret: str = "pynuxt-social-dev-secret-change-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24 * 7
    db_path: str = "data.db"

    @property
    def db_uri(self) -> str:
        return f"sqlite:///{self.db_path}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings():
    return Settings()
```

---

#### P1-5: 引入 Alpine.js 提升客户端交互体验

**位置**：[frontend/layouts/default.html](frontend/layouts/default.html)

**目标**：
- 解决 Feed Tab 同步问题
- 添加字数实时统计
- 避免手动"粘合" HTMX 和状态

**实施步骤**：
1. 在 `default.html` 引入 Alpine.js
2. 重构 `feed.html`，用 `x-data` 管理状态
3. 动态同步 `feed` 参数和 Tab 高亮

```html
<!-- 引入 -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>

<!-- feed.html 重构 -->
<div x-data="{ tab: 'global', content: '' }">
    <div class="tabs">
        <a 
            :class="{'tab active': tab === 'global', 'tab': tab !== 'global'}"
            @click="tab = 'global'"
            hx-get="/bff/posts?feed=global"
            hx-target="#post-list"
        >
            全局
        </a>
        <a 
            :class="{'tab active': tab === 'following', 'tab': tab !== 'following'}"
            @click="tab = 'following'"
            hx-get="/bff/posts?feed=following"
            hx-target="#post-list"
        >
            关注
        </a>
    </div>

    <form 
        hx-post="/bff/posts" 
        hx-target="#post-list"
        hx-vals="{'feed': tab}"
    >
        <textarea 
            name="content" 
            x-model="content"
            maxlength="280"
        ></textarea>
        <span x-text="280 - content.length + ' 字剩余'"></span>
        <button type="submit" :disabled="content.trim() === ''">发布</button>
    </form>
</div>
```

---

### P2 — 建议修复（影响可维护性）

#### P2-1: `create_post` 参数来源不一致

**位置**：[frontend/bff_core.py#L63-66](frontend/bff_core.py#L63-66)

**问题**：`feed` 用 Query 参数，`content` 用 Form 参数，来源不统一。

**修复方案**：统一为 Form 参数

---

#### P2-2: followers/following 返回相同数据

**位置**：[backend/routers/users.py](backend/routers/users.py) — `get_followers`/`get_following`

**问题**：好友关系是双向的，两接口查询逻辑相同，返回数据一样。

---

#### P2-3: 无统一环境变量加载

**位置**：项目根目录缺少 `.env` 文件和加载逻辑

**问题**：环境变量分散在代码中，无统一管理。

**修复方案**：添加 `python-dotenv`

```bash
pip install python-dotenv
```

```python
# backend/main.py / frontend/main.py
from dotenv import load_dotenv
load_dotenv()
```

```ini
# .env 文件（项目根目录）
JWT_SECRET=pynuxt-social-dev-secret-change-in-prod
API_BASE=http://localhost:8012
DEBUG=True
```

---

### P3 — 未来改进（不紧急）

#### P3-1: 无分页 UI

#### P3-2: 无删除/编辑帖子功能

#### P3-3: BFFBase 克隆模式历史包袱

#### P3-4: 模板渲染升级为异步（可选）

---

## 三、参考 FastBlocks 的改进建议（第三阶段）

通过分析 `fastblocks` 仓库，可在第三阶段实施：

| 项 | 来源 | 收益 |
|----|------|------|
| CSRF 中间件 | fastblocks/middleware.py | 提升安全性 |
| HtmxResponse 类 | fastblocks/htmx.py | 简化 HTMX 响应处理 |
| 响应压缩 (Brotli) | fastblocks/middleware.py | 提升加载速度 |
| 中间件顺序枚举 | fastblocks/middleware.py | 规范代码架构 |

---

## 四、已使用成熟组件（无需替换）

| 部分 | 当前实现 | 评价 |
|------|---------|------|
| 密码哈希 | `passlib[bcrypt]` | ✅ 完美，保持 |
| 数据库 ORM | `SQLAlchemy 2.0` | ✅ 完美，保持 |
| 静态文件 | `FastAPI StaticFiles` | ✅ 完美，保持 |
| 异步 HTTP 客户端 | `httpx` | ✅ 完美，保持 |
| 数据验证 | `pydantic 2.0` | ✅ 完美，保持 |
| 模板引擎 | `Jinja2` | ✅ 完美，保持 |
| API 框架 | `FastAPI` | ✅ 完美，保持 |

---

## 五、分阶段任务清单

### 第一阶段：稳定性（2-3 天）

- [ ] 修复 N+1 查询问题
- [ ] 替换 `datetime.utcnow()` 为 `datetime.now(timezone.utc)`
- [ ] 配置管理替换为 pydantic-settings

### 第二阶段：体验优化（1-2 天）

- [ ] 隐藏公开 API 的 email 字段
- [ ] 修复 `_user_cache` 全局变量问题
- [ ] 引入 python-dotenv + .env 文件
- [ ] 引入 Alpine.js 并重构 feed.html

### 第三阶段：框架升级（可选，按需求）

- [ ] 添加 CSRF 中间件
- [ ] 添加 HtmxResponse 类
- [ ] 添加响应压缩
- [ ] 重构中间件架构
