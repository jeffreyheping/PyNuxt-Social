# PyNuxt-Social 系统架构设计

## 1. 技术选型确认

| 层次 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **后端框架** | FastAPI | ≥0.100.0 | 纯 JSON REST API，不感知前端 |
| **ORM** | SQLAlchemy | ≥2.0.0 | 声明式模型 + session 依赖注入 |
| **数据库** | SQLite | 内置 | 单文件 `data.db`，开发用 |
| **认证** | python-jose + passlib | ≥3.3.0 / ≥1.7.4 | JWT 签发 + bcrypt 密码哈希 |
| **前端框架** | FastAPI | ≥0.100.0 | BFF 层，独立进程 |
| **模板引擎** | Jinja2 | ≥3.1.0 | 继承 PyNuxt 框架全局 env |
| **交互** | HTMX | 1.9.x | htmx.min.js，0 自定义 JS |
| **HTTP 客户端** | httpx | ≥0.24.0 | BFFBase 内置异步客户端 |
| **样式** | 原生 CSS | — | 无 UI 框架，style.css 统一 |
| **数据验证** | Pydantic | ≥2.0.0 | 请求/响应 Schema |

### 架构模式

- **后端**：经典三层 — Router → Service(隐含在 Router 内) → SQLAlchemy Model
- **前端**：BFF 模式 — `main.py` 路由 → `bff_core.py` 业务 → `pynuxt/bff.py` 框架基座
- **认证**：后端签发 JWT → 前端存 Cookie(HttpOnly) → BFF 转发 Authorization Header

---

## 2. 文件清单

### 后端（`backend/`）

| 相对路径 | 职责 |
|----------|------|
| `backend/main.py` | FastAPI 入口，创建表、注册路由、根路径信息 |
| `backend/config.py` | 配置：DB_PATH、DB_URI、JWT_SECRET 等 |
| `backend/database.py` | SQLAlchemy engine/session/Base/get_db |
| `backend/models.py` | ORM 模型：User, Post, Like, FriendRequest |
| `backend/schemas.py` | ❌ 未独立创建，Schema 内联于各 router |
| `backend/routers/__init__.py` | 路由模块导入 |
| `backend/routers/auth.py` | 认证路由：register, login, logout, me, JWT 工具函数 |
| `backend/routers/users.py` | 用户路由：搜索、详情、帖子列表、粉丝/关注列表 |
| `backend/routers/posts.py` | 帖子路由：动态流(全局/关注)、发帖、点赞 toggle、点赞状态 |
| `backend/routers/friends.py` | 好友路由：发送请求、待处理列表、接受/拒绝、关系状态 |

### 前端（`frontend/`）

| 相对路径 | 职责 |
|----------|------|
| `frontend/main.py` | FastAPI BFF 入口，注册 API 路由 + 文件系统路由 |
| `frontend/config.py` | 配置：API_BASE, PORT, DEBUG, PAGES_DIR, TEMPLATE_DIRS |
| `frontend/bff_core.py` | BFF 业务子类：AuthBFF, FeedBFF, UserBFF, FriendBFF |
| `frontend/pynuxt/__init__.py` | 框架层（✅ v0.3.0 已改进） |
| `frontend/pynuxt/bff.py` | BFFBase 基座（✅ 新增 _post_form/_put_form/refresh_params/timeout） |
| `frontend/pynuxt/routing.py` | 文件系统路由引擎（✅ 新增 async context_vars 支持） |
| `frontend/pynuxt/auth.py` | Token/Cookie 依赖注入（✅ 共享 httpx 客户端 + get_context_user） |
| `frontend/pynuxt/templates.py` | Jinja2 env 单例（✅ 重写为 _LazyEnv + configure_env） |
| `frontend/pynuxt/errors.py` | 错误处理（✅ 401 自动重定向 login_path） |
| `frontend/pynuxt/middleware.py` | 🆕 登录态守卫中间件（原设计无此文件） |

### 前端模板

| 相对路径 | 职责 |
|----------|------|
| `frontend/layouts/default.html` | 主布局：导航栏 + 登录状态 + 内容区 |
| `frontend/pages/index.html` | 首页：重定向逻辑 |
| `frontend/pages/login.html` | 登录页 |
| `frontend/pages/register.html` | 注册页 |
| `frontend/pages/feed.html` | 动态流页：双 Tab + 发帖框 |
| `frontend/pages/search.html` | 用户搜索页 |
| `frontend/pages/friends.html` | 好友请求管理页 |
| `frontend/pages/users/[username]/index.html` | 用户主页 |
| `frontend/pages/users/[username]/followers.html` | 粉丝列表页 |
| `frontend/pages/users/[username]/following.html` | 关注列表页 |
| `frontend/components/post_item.html` | 单条帖子片段 |
| `frontend/components/post_list.html` | 帖子列表片段 |
| `frontend/components/like_button.html` | 点赞按钮片段 |
| `frontend/components/friend_button.html` | 好友操作按钮片段 |
| `frontend/components/friend_request_item.html` | 单条好友请求片段 |
| `frontend/components/user_card.html` | 用户卡片片段 |
| `frontend/components/search_results.html` | 搜索结果片段 |
| `frontend/static/css/style.css` | 全局样式 |
| `frontend/static/js/htmx.min.js` | HTMX 库 |

### 根目录

| 相对路径 | 职责 |
|----------|------|
| `seed_data.py` | 种子数据脚本：10 用户 × 5 帖子 + 好友关系 |
| `requirements.txt` | Python 依赖清单 |
| `start-all.ps1` | 一键启动后端 + 前端 |
| `README.md` | 项目说明 |

---

## 3. 数据库 Schema（SQLAlchemy 模型细节）

### 3.1 User 表

```python
class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(50), unique=True, nullable=False, index=True)
    email         = Column(String(100), unique=True, nullable=False, index=True)
    display_name  = Column(String(100), nullable=True)       # 可选昵称，默认=username
    password_hash = Column(String(255), nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)
```

**索引**：`username`(UNIQUE), `email`(UNIQUE)

### 3.2 Post 表

```python
class Post(Base):
    __tablename__ = "posts"

    id         = Column(Integer, primary_key=True, index=True)
    author_id  = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content    = Column(String(280), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    author = relationship("User", backref="posts")
    likes  = relationship("Like", back_populates="post", cascade="all, delete-orphan")
```

**索引**：`author_id`(FK), `created_at`(排序)

### 3.3 Like 表

```python
class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_like_user_post"),)

    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)

    user = relationship("User", backref="likes")
    post = relationship("Post", back_populates="likes")
```

**约束**：`UNIQUE(user_id, post_id)` — 每人每帖最多一个赞

### 3.4 FriendRequest 表

```python
class FriendRequest(Base):
    __tablename__ = "friend_requests"

    id           = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    to_user_id   = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status       = Column(String(20), nullable=False, default="pending")  # pending | accepted | rejected
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    from_user = relationship("User", foreign_keys=[from_user_id], backref="sent_requests")
    to_user   = relationship("User", foreign_keys=[to_user_id], backref="received_requests")

    __table_args__ = (
        UniqueConstraint("from_user_id", "to_user_id", name="uq_friend_request"),
        Index("ix_friend_request_to_status", "to_user_id", "status"),  # 查待处理
    )
```

**约束**：`UNIQUE(from_user_id, to_user_id)` — 同一对用户只能有一条请求记录

### 好友关系查询逻辑

accepted 即双向关注，无单独 Follow 表。

- **查询 A 关注了谁**：找出 `(from_user_id=A AND status=accepted)` 的 `to_user_id` ∪ `(to_user_id=A AND status=accepted)` 的 `from_user_id`
- **查询 A 的粉丝**：同上，方向互换
- **关注 Tab 帖子**：先找出 A 的所有 accepted 好友 ID，再查 `Post.author_id IN (好友IDs)`

---

## 4. 后端 API 接口规范

### 4.1 认证 `/api/auth`

#### POST /api/auth/register

- **认证**：无需
- **请求**：
```json
{
  "username": "string(2-50)",
  "email": "string(email)",
  "password": "string(6+)"
}
```
- **响应 201**：
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer",
  "user": { "id": 1, "username": "alice", "email": "a@b.com", "display_name": "Alice" }
}
```
- **错误**：400 用户名已存在 / 400 邮箱已注册

#### POST /api/auth/login

- **认证**：无需
- **请求**：
```json
{
  "username": "string",
  "password": "string"
}
```
- **响应 200**：同 register 响应格式
- **错误**：401 用户名或密码错误

#### POST /api/auth/logout

- **认证**：无需（JWT 无状态，前端删 Cookie 即可）
- **响应 200**：`{"message": "已登出"}`

#### GET /api/auth/me

- **认证**：必须（Bearer Token）
- **响应 200**：
```json
{ "id": 1, "username": "alice", "email": "a@b.com", "display_name": "Alice", "created_at": "ISO8601" }
```
- **错误**：401 未登录

---

### 4.2 帖子 `/api/posts`

#### GET /api/posts?feed=global|following&skip=0&limit=20

- **认证**：可选（following 模式必须）
- **参数**：
  - `feed`：`global`(默认) 或 `following`
  - `skip`：偏移量，默认 0
  - `limit`：每页数量，默认 20
- **响应 200**：
```json
[
  {
    "id": 1,
    "author": { "id": 1, "username": "alice", "display_name": "Alice" },
    "content": "Hello world!",
    "created_at": "ISO8601",
    "like_count": 3,
    "liked_by_me": false
  }
]
```
- **逻辑**：
  - `global`：查所有帖子，按 created_at DESC
  - `following`：先查当前用户 accepted 好友，再查其帖子
  - `liked_by_me`：当前登录用户是否对该帖点了赞（未登录则 false）
  - `like_count`：该帖的 Like 总数

#### POST /api/posts

- **认证**：必须
- **请求**：
```json
{ "content": "string(1-280)" }
```
- **响应 201**：
```json
{
  "id": 10,
  "author": { "id": 1, "username": "alice", "display_name": "Alice" },
  "content": "新帖子",
  "created_at": "ISO8601",
  "like_count": 0,
  "liked_by_me": false
}
```
- **错误**：401 未登录 / 422 内容为空或超长

#### POST /api/posts/{id}/like

- **认证**：必须
- **逻辑**：Toggle — 已赞则取消，未赞则添加
- **响应 200**：
```json
{ "liked": true, "like_count": 4 }
```
或
```json
{ "liked": false, "like_count": 3 }
```
- **错误**：401 未登录 / 404 帖子不存在

#### GET /api/posts/{id}/like/status

- **认证**：必须
- **响应 200**：
```json
{ "liked": true, "like_count": 4 }
```
- **错误**：401 未登录 / 404 帖子不存在

---

### 4.3 用户 `/api/users`

#### GET /api/users?q=keyword

- **认证**：无需
- **参数**：`q` — 搜索关键词（匹配 username 或 display_name，模糊匹配）
- **响应 200**：
```json
[
  { "id": 1, "username": "alice", "display_name": "Alice", "created_at": "ISO8601" }
]
```

#### GET /api/users/{username}

- **认证**：无需
- **响应 200**：
```json
{
  "id": 1, "username": "alice", "display_name": "Alice",
  "email": "a@b.com", "created_at": "ISO8601",
  "post_count": 5, "follower_count": 3, "following_count": 2
}
```
- **错误**：404 用户不存在

#### GET /api/users/{username}/posts?skip=0&limit=20

- **认证**：可选（决定 liked_by_me）
- **响应 200**：帖子数组（同 /api/posts 的元素格式）

#### GET /api/users/{username}/followers

- **认证**：无需
- **响应 200**：
```json
[
  { "id": 2, "username": "bob", "display_name": "Bob", "created_at": "ISO8601" }
]
```

#### GET /api/users/{username}/following

- **认证**：无需
- **响应 200**：同 followers 格式

---

### 4.4 好友 `/api/friends`

#### GET /api/friends/requests

- **认证**：必须
- **响应 200**：
```json
[
  {
    "id": 1,
    "from_user": { "id": 2, "username": "bob", "display_name": "Bob" },
    "status": "pending",
    "created_at": "ISO8601"
  }
]
```
- **说明**：返回当前用户收到的 `pending` 请求列表

#### POST /api/friends/requests/{username}

- **认证**：必须
- **逻辑**：向目标用户发送好友请求
- **响应 201**：
```json
{
  "id": 5,
  "from_user_id": 1, "to_user_id": 2,
  "status": "pending", "created_at": "ISO8601"
}
```
- **错误**：401 未登录 / 404 目标用户不存在 / 400 已发送过 / 400 不能向自己发送

#### PUT /api/friends/requests/{id}

- **认证**：必须
- **请求**：
```json
{ "action": "accept" }   // 或 "reject"
```
- **响应 200**：
```json
{ "id": 1, "status": "accepted" }
```
- **错误**：401 未登录 / 404 请求不存在 / 403 非请求接收者 / 400 状态非 pending

#### GET /api/friends/status/{username}

- **认证**：必须
- **响应 200**：
```json
{ "status": "none" }       // 无关系
{ "status": "pending" }    // 已发送请求（当前用户发出的）
{ "status": "pending_received" }  // 收到对方请求（当前用户待处理）
{ "status": "accepted" }   // 已是好友
{ "status": "rejected" }   // 已被拒绝（当前用户发出的被拒绝）
{ "status": "self" }       // 自己
```

---

## 5. 前端 BFF 方法规划

### 5.1 AuthBFF

| 方法 | 调用 API | 渲染组件 | 说明 |
|------|---------|---------|------|
| `login(username, password)` | POST /api/auth/login | — | 返回 token dict，由 main.py 设 Cookie |
| `register(username, email, password)` | POST /api/auth/register | — | 返回 token dict，由 main.py 设 Cookie |
| `get_status_html(user)` | — | 内联 HTML | 登录状态栏：欢迎信息+登出 / 登录注册链接 |
| `get_nav_html(user)` | — | 内联 HTML | 导航栏含用户信息 |

### 5.2 FeedBFF

| 方法 | 调用 API | 渲染组件 | 说明 |
|------|---------|---------|------|
| `get_posts(feed, skip, limit)` | GET /api/posts?feed=&skip=&limit= | post_list.html | 动态流列表 |
| `create_post(content)` | POST /api/posts | post_list.html | 发帖后刷新列表 |
| `toggle_like(post_id)` | POST /api/posts/{id}/like | like_button.html | 点赞/取消赞 |
| `get_like_button(post_id)` | GET /api/posts/{id}/like/status | like_button.html | 获取点赞状态 |

### 5.3 UserBFF

| 方法 | 调用 API | 渲染组件 | 说明 |
|------|---------|---------|------|
| `search_users(q)` | GET /api/users?q= | search_results.html | 搜索结果 |
| `get_user_profile(username)` | GET /api/users/{username} | 页面内渲染 | 用户信息 |
| `get_user_posts(username, skip, limit)` | GET /api/users/{username}/posts | post_list.html | 用户帖子 |
| `get_followers(username)` | GET /api/users/{username}/followers | user_card 列表 | 粉丝 |
| `get_following(username)` | GET /api/users/{username}/following | user_card 列表 | 关注 |

### 5.4 FriendBFF

| 方法 | 调用 API | 渲染组件 | 说明 |
|------|---------|---------|------|
| `get_pending_requests()` | GET /api/friends/requests | friend_request_item 列表 | 待处理列表 |
| `send_request(username)` | POST /api/friends/requests/{username} | friend_button.html | 发送好友请求 |
| `respond_request(id, action)` | PUT /api/friends/requests/{id} | friend_request_item 或 friend_button | 接受/拒绝 |
| `get_friend_status(username)` | GET /api/friends/status/{username} | friend_button.html | 关系状态按钮 |

---

## 6. HTMX 交互流

### 6.1 登录/注册

| 交互 | 触发 | hx-* | 目标 | 返回 |
|------|------|-------|------|------|
| 登录提交 | `<form hx-post="/bff/auth/login">` | hx-post, hx-target="#auth-message" | #auth-message | 成功→HX-Redirect:/feed；失败→错误片段 |
| 注册提交 | `<form hx-post="/bff/auth/register">` | hx-post, hx-target="#auth-message" | #auth-message | 同上 |
| 登出 | `<button hx-post="/bff/auth/logout">` | hx-post, hx-swap="none" | — | 删 Cookie + HX-Redirect:/ |

### 6.2 动态流

| 交互 | 触发 | hx-* | 目标 | 返回 |
|------|------|-------|------|------|
| 加载帖子 | `#post-list hx-get="/bff/posts?feed=global"` | hx-get, hx-trigger="load" | #post-list | post_list.html |
| 切换 Tab | `<a hx-get="/bff/posts?feed=following">` | hx-get, hx-target="#post-list" | #post-list | post_list.html |
| 发帖 | `<form hx-post="/bff/posts">` | hx-post, hx-target="#post-list" | #post-list | post_list.html |
| 点赞 | `<button hx-post="/bff/posts/{id}/like">` | hx-post, hx-target="#like-btn-{id}", hx-swap="outerHTML" | #like-btn-{id} | like_button.html |

### 6.3 好友

| 交互 | 触发 | hx-* | 目标 | 返回 |
|------|------|-------|------|------|
| 加载好友按钮 | `#friend-btn hx-get="/bff/friends/status/{username}"` | hx-get, hx-trigger="load" | #friend-btn | friend_button.html |
| 发送请求 | `<button hx-post="/bff/friends/requests/{username}">` | hx-post, hx-target="#friend-btn", hx-swap="outerHTML" | #friend-btn | friend_button.html (pending) |
| 接受请求 | `<button hx-put="/bff/friends/requests/{id}" hx-vals='{"action":"accept"}'>` | hx-put, hx-target="#request-{id}", hx-swap="outerHTML" | #request-{id} | friend_request_item.html (accepted) |
| 拒绝请求 | `<button hx-put="/bff/friends/requests/{id}" hx-vals='{"action":"reject"}'>` | hx-put, hx-target="#request-{id}", hx-swap="outerHTML" | #request-{id} | 移除该项 |

### 6.4 搜索

| 交互 | 触发 | hx-* | 目标 | 返回 |
|------|------|-------|------|------|
| 实时搜索 | `<input hx-get="/bff/users/search" hx-trigger="input changed delay:300ms">` | hx-get, hx-target="#search-results" | #search-results | search_results.html |

---

## 7. 任务列表

### T01: 项目基础设施

**文件**：
- `requirements.txt`
- `start-all.ps1`
- `backend/config.py`
- `backend/database.py`
- `backend/main.py`
- `backend/routers/__init__.py`
- `frontend/config.py`
- `frontend/main.py`（骨架，注册空路由）
- `frontend/pynuxt/__init__.py`
- `frontend/pynuxt/bff.py`
- `frontend/pynuxt/routing.py`
- `frontend/pynuxt/auth.py`
- `frontend/pynuxt/templates.py`
- `frontend/pynuxt/errors.py`
- `frontend/layouts/default.html`
- `frontend/static/css/style.css`
- `frontend/static/js/htmx.min.js`

**具体内容**：
1. 创建 `requirements.txt`，内容见第 8 节
2. 从 PyNuxt 原样复制 `frontend/pynuxt/` 6 个框架文件
3. `backend/config.py`：设置 DB_PATH=`项目根/data.db`、DB_URI、JWT_SECRET 等
4. `backend/database.py`：engine + SessionLocal + Base + get_db（同 PyNuxt）
5. `backend/main.py`：FastAPI 入口骨架，预留 router 注册
6. `backend/routers/__init__.py`：导入四个路由模块
7. `frontend/config.py`：API_BASE=`http://localhost:8012`、PORT=3000、DEBUG=True 等
8. `frontend/main.py`：FastAPI 入口骨架，挂载 static、注册 BFF 路由占位、安装文件系统路由
9. `frontend/layouts/default.html`：主布局，含导航栏（首页/搜索/好友/登录状态）、htmx.min.js
10. `frontend/static/css/style.css`：基础样式（从 PyNuxt 继承 + 社交扩展）
11. 下载 `htmx.min.js` 到 `frontend/static/js/`
12. `start-all.ps1`：启动后端(8012) + 前端(3000)

**依赖**：无

---

### T02: 后端数据层 + API

**文件**：
- `backend/models.py`
- `backend/schemas.py`
- `backend/routers/auth.py`
- `backend/routers/users.py`
- `backend/routers/posts.py`
- `backend/routers/friends.py`

**具体内容**：
1. `models.py`：定义 User, Post, Like, FriendRequest 四个 ORM 模型（详见第 3 节）
2. `schemas.py`：定义所有 Pydantic Schema（详见第 4 节中的请求/响应格式）
3. `auth.py`：
   - 复用 PyNuxt 的 JWT 工具函数（create_access_token, verify_password, get_password_hash）
   - get_current_user / get_current_user_optional 依赖注入
   - register / login / logout / me 四个端点
4. `posts.py`：
   - GET /api/posts（feed=global|following, skip, limit）— 含 like_count 和 liked_by_me 计算
   - POST /api/posts — 需认证
   - POST /api/posts/{id}/like — Toggle 点赞
   - GET /api/posts/{id}/like/status — 点赞状态
5. `users.py`：
   - GET /api/users?q= — 模糊搜索
   - GET /api/users/{username} — 用户详情含 post_count/follower_count/following_count
   - GET /api/users/{username}/posts — 该用户帖子
   - GET /api/users/{username}/followers — 粉丝列表
   - GET /api/users/{username}/following — 关注列表
6. `friends.py`：
   - GET /api/friends/requests — 当前用户收到的 pending 请求
   - POST /api/friends/requests/{username} — 发送请求
   - PUT /api/friends/requests/{id} — 接受/拒绝
   - GET /api/friends/status/{username} — 关系状态
7. 在 `backend/main.py` 中注册所有路由，确保 `Base.metadata.create_all(bind=engine)` 创建所有表

**依赖**：T01

---

### T03: 前端 BFF 层 + 页面模板

**文件**：
- `frontend/bff_core.py`
- `frontend/components/post_item.html`
- `frontend/components/post_list.html`
- `frontend/components/like_button.html`
- `frontend/components/friend_button.html`
- `frontend/components/friend_request_item.html`
- `frontend/components/user_card.html`
- `frontend/components/search_results.html`
- `frontend/pages/index.html`
- `frontend/pages/login.html`
- `frontend/pages/register.html`
- `frontend/pages/feed.html`
- `frontend/pages/search.html`
- `frontend/pages/friends.html`
- `frontend/pages/users/[username]/index.html`
- `frontend/pages/users/[username]/followers.html`
- `frontend/pages/users/[username]/following.html`

**具体内容**：
1. `bff_core.py`：实现 AuthBFF, FeedBFF, UserBFF, FriendBFF 四个类（详见第 5 节）
2. 在 `frontend/main.py` 中注册所有 BFF 路由：
   - /bff/auth/login, /bff/auth/register, /bff/auth/logout, /bff/auth/status
   - /bff/posts, /bff/posts?feed=, /bff/posts/{id}/like
   - /bff/users/search?q=, /bff/users/{username}/posts, /bff/users/{username}/followers, /bff/users/{username}/following
   - /bff/friends/requests, /bff/friends/requests/{username}, /bff/friends/requests/{id}, /bff/friends/status/{username}
3. 7 个组件模板（HTMX 片段）
4. 9 个页面模板（含布局继承）
5. 所有页面中 HTMX 属性按第 6 节规范编写

**依赖**：T01

---

### T04: 种子数据 + 集成调试

**文件**：
- `seed_data.py`
- `README.md`

**具体内容**：
1. `seed_data.py`：
   - 创建 10 个用户（username: user01-user10，display_name: 用户一~用户十）
   - 每用户 5 条帖子（共 50 条）
   - 好友关系：user01↔user02, user01↔user03, user02↔user03（accepted），user04→user01（pending）
   - 点赞数据：随机若干点赞
   - 运行方式：`python seed_data.py`（先删后建，幂等）
2. `README.md`：项目说明、启动步骤、端口说明
3. 端到端验证：
   - 启动后端 + 前端
   - 测试注册/登录流程
   - 测试发帖/动态流
   - 测试点赞
   - 测试好友请求流程
   - 测试搜索
   - 测试用户主页
   - 修复发现的问题

**依赖**：T02, T03

---

### 任务依赖关系

```
T01 (基础设施)
├── T02 (后端数据层+API)
└── T03 (前端BFF+模板)
    └── T04 (种子数据+集成) ← 也依赖 T02
```

T02 和 T03 可以并行开发（都只依赖 T01），但 T04 需要两者都完成。

---

## 8. 依赖包清单

```
# requirements.txt
fastapi>=0.100.0
uvicorn>=0.23.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
pydantic[email]>=2.0.0
jinja2>=3.1.0
httpx>=0.24.0
python-multipart>=0.0.6
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
bcrypt==4.0.1
email-validator>=2.0.0
```

---

## 9. 跨文件共享约定

### 9.1 数据库会话管理

- 后端所有路由通过 `Depends(get_db)` 获取 Session，用完自动关闭
- 无全局 Session，每个请求独立 Session
- `get_db()` 定义在 `backend/database.py`，使用 `yield` 模式

### 9.2 认证 Token 传递链路

```
浏览器 Cookie(auth_token) → 前端 FastAPI(Cookie 依赖注入)
  → BFFBase.with_auth(token) → self._get_headers()["Authorization"] = "Bearer {token}"
  → 后端 FastAPI(OAuth2PasswordBearer) → get_current_user 解析 JWT
```

- 前端登录/注册成功时，`main.py` 通过 `response.set_cookie()` 设置 `auth_token`（HttpOnly, SameSite=Lax, max_age=7天）
- 前端登出时，`main.py` 通过 `response.delete_cookie()` 删除 Cookie
- `frontend/pynuxt/auth.py` 的 `get_token` 从 Cookie/Header 提取 token
- `frontend/pynuxt/auth.py` 的 `get_current_user_id` / `get_optional_user_id` / `get_optional_user` 通过调用后端 `/api/auth/me` 验证 token 并获取用户信息
- BFF 路由通过 `Depends(get_token)` 获取 token，传给 `bff.with_auth(token)`

### 9.3 HTMX 片段 vs 完整页面判断规则

| 场景 | 返回类型 | 判断方式 |
|------|---------|---------|
| 整页导航（首次访问 URL） | 完整 HTML（含 layout） | 文件系统路由自动渲染 pages/*.html |
| HTMX 局部交互（hx-get/hx-post） | HTML 片段 | BFF 路由返回组件渲染结果 |
| 表单提交成功（登录/注册） | HX-Redirect | response.headers["HX-Redirect"] = "/feed" |
| 表单提交失败 | HTML 错误片段 | 替换 #auth-message |
| 点赞/好友按钮 | HTML 片段 | 替换按钮自身（hx-swap="outerHTML"） |

### 9.4 错误处理约定

- **后端**：使用 `HTTPException(status_code, detail)`，返回 `{"detail": "错误信息"}`
- **前端 BFF**：`BFFError` 异常被 `setup_exception_handlers` 捕获，渲染错误页面
- **HTMX 请求出错**：返回错误 HTML 片段，替换目标区域
- **4xx 客户端错误**：友好提示（用户名已存在、密码错误等）
- **5xx 服务端错误**：DEBUG=True 显示详细 traceback，False 显示友好提示

### 9.5 统一响应格式（后端 API）

- 列表接口返回 `[]`（空列表而非 null）
- 对象接口返回 `{}` 格式
- 所有 datetime 字段返回 ISO 8601 UTC 字符串
- 分页通过 `skip` + `limit` 参数实现，不返回总数（简化）

### 9.6 前端路由前缀约定

- BFF 路由前缀统一为 `/bff/`（如 `/bff/posts`, `/bff/auth/login`），避免与文件系统路由冲突
- 文件系统路由（`pages/`）负责整页渲染
- BFF 路由负责 HTMX 片段渲染和表单处理（登录/注册/登出）

### 9.7 模板变量约定

- 所有页面模板通过 `context_vars` 回调获取：`current_user`（dict|None）、`request`
- 组件模板通过 BFF `_render()` 传参：`data`（API 数据）、`current_user_id`（int|None）
- 导航栏状态通过 `hx-get="/bff/auth/status"` 动态加载（HTMX load trigger）

### 9.8 登录态守卫（P1-03）

- 前端 BFF 路由中对需要登录的端点使用 `Depends(get_current_user_id)`
- 未登录访问受保护页面时，`get_current_user_id` 抛出 401，被异常处理器捕获
- 异常处理器对非 HTMX 请求返回重定向 HTML（`<meta http-equiv="refresh" content="0;url=/login">`）
- 对 HTMX 请求返回 `HX-Redirect: /login` 头

---

## 10. 复盘：设计 vs 实际偏差（2026-06-05）

> 以下为项目完成后复盘发现的偏差、遗漏和设计缺陷。

### 10.1 文件级偏差

| 设计 | 实际 | 说明 |
|------|------|------|
| `backend/schemas.py` 独立文件 | Schema 内联于各 router | 小项目无所谓，但如后续复用 Schema 应独立 |
| pynuxt/ 6 个文件"从 PyNuxt 复制不改" | 全部改了 + 新增 middleware.py | 设计阶段低估了框架能力缺口 |
| 无 middleware.py | 新增 `LoginGuardMiddleware` | 原设计依赖路由级 401 拦截，不够优雅 |

### 10.2 设计缺陷（已知但未修复）

| # | 缺陷 | 影响 | 严重度 |
|---|------|------|--------|
| D1 | **followers/following 返回相同数据** | 好友关系是双向的，followers 和 following 实际上是同一批人，命名误导 | 中 |
| D2 | **用户邮箱在公开 API 暴露** | `GET /api/users/{username}` 返回 email 字段，隐私泄漏 | 高 |
| D3 | **Feed Tab 与发帖表单不同步** | 切换到"关注"Tab 后发帖，hidden input 仍为 global，刷新错误列表 | 中 |
| D4 | **无分页 UI** | API 支持 skip/limit，但前端无"加载更多"按钮 | 低 |
| D5 | **无删除帖子功能** | 用户无法删除自己发的帖子 | 低 |
| D6 | **无编辑个人资料功能** | 无法修改 display_name/email/密码 | 低 |
| D6 | **N+1 查询** | `_serialize_post` 每条帖子 3 次独立查询（author/like_count/liked_by_me），20 条 = 60+ SQL | 中 |
| D7 | **`datetime.utcnow()` 已弃用** | Python 3.12+ 弃用，应用 `datetime.now(timezone.utc)` | 低 |
| D8 | **AuthBFF.get_status_html() 返回硬编码 HTML** | 绕过 Jinja2 模板系统，破坏"所有渲染走模板"原则 | 低 |
| D9 | **BFFBase 构造函数的 template_dirs 参数无效** | 传入但从不使用，误导开发者 | 低 |
| D10 | **`_action_then_refresh()` 从未被调用** | 设计的通用 CRUD 辅助方法，实际 BFF 都手动实现了"调 API → 渲染" | 中 |
| D11 | **httpx.AsyncClient 无 shutdown 钩子** | `bff.close()` 存在但从未在 app lifespan 中调用，连接泄漏 | 中 |
| D12 | **无 CSRF 防护** | HTMX 表单提交无 CSRF Token | 中 |

### 10.3 后端数据模型问题

**FriendRequest 的 UNIQUE 约束 vs 双向查询矛盾**：
- `UNIQUE(from_user_id, to_user_id)` 只约束单方向
- 但 `send_request` 查询时用 OR 条件查双向
- 被拒绝后重新申请时，代码翻转了 from/to 方向并更新同一条记录
- 这意味着 UNIQUE 约束实际上无法防止 A→B 和 B→A 并存（代码保证了逻辑唯一，但约束不完整）

**建议**：如果未来要严格约束，应改为在应用层保证 "小 ID 在前" 或使用数据库 CHECK 约束。
