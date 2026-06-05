<p align="center">
  <strong>PyNuxt-Social</strong><br>
  一个用纯 Python 实现的社交平台 —— 也是 PyNuxt 框架的参考实现
</p>

---

## 目录

- [缘起](#缘起)
- [核心信念](#核心信念)
- [技术架构](#技术架构)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [核心设计](#核心设计)
- [踩过的坑](#踩过的坑)
- [意义与启示](#意义与启示)
- [下一步](#下一步)

---

## 缘起

PyNuxt-Social 的故事始于一个简单的问题：

> **Python 能不能像 Nuxt.js 那样做全栈开发？**

2024 年的前端世界已经被 React/Vue/Svelte 席卷。写一个社交平台，标准路径是：Node.js 后端 + React 前端 + WebSocket 实时推送。但你如果是一个 Python 开发者 —— 熟悉 FastAPI，熟悉 SQLAlchemy，熟悉 Jinja2 —— 你会本能地想：为什么非得切换语言？

PyNuxt-Social 就是这个念头的一次完整实践。

我们不写 JavaScript（好吧，除了一个 htmx.min.js），不写 TypeScript，不搞 webpack/vite 构建。只用 Python，从后端 API 到前端渲染，全链路 Python。

当然，这不是一个玩具项目。它是一个有完整用户系统的社交平台 —— 注册登录、发帖点赞、好友关系、动态流 —— 同时也是 **PyNuxt 框架（v0.5.1）** 的第一个参考实现。

---

## 核心信念

这个项目建立在三个信念之上：

### 1. SSR 没有死

2019 年以后，SSR（服务端渲染）一度被视为旧时代的遗产。大家都在聊 SPA、CSR、Islands Architecture。但 HTMX 的出现告诉我们：**HTML 一直在那里，只是我们太急于用 JavaScript 替换它了。**

PyNuxt-Social 的每一个交互 —— 发帖、点赞、搜索、好友请求 —— 都是服务端返回 HTML 片段，由 HTMX 做局部替换。没有 Virtual DOM，没有状态管理，没有客户端路由。体验流畅，代码量极少。

### 2. BFF 是被忽视的架构

Backend For Frontend 不是微服务的专利。在中小型项目中，一个 BFF 层能带来意想不到的清晰度：

- 后端只关心数据（纯 JSON REST API）
- 前端只关心展示（调 API + 渲染模板）
- 两层独立部署、独立演进、独立扩容

PyNuxt-Social 跑着两个 FastAPI 进程 —— 端口 8012 的后端和端口 3000 的前端 BFF —— 各司其职，互不干扰。

### 3. 框架应该从实战中来

PyNuxt 不是在白纸上设计出来的。它从 PyNuxt-Social 的代码中提取、沉淀、打磨。每一次"这样写不舒服"的抱怨，都变成了一次框架层的改进。

`pynuxt/` 目录里的每一行代码，都是被真实需求驱动的。

---

## 技术架构

```
┌──────────────────────────────────────────────────────────┐
│                      浏览器                              │
│  htmx.min.js（唯一的 JS 运行时）                           │
└──────────┬──────────────────────────────┬────────────────┘
           │ HTMX 请求                     │ 页面请求
           ▼                              ▼
┌──────────────────────────────────────────────────────────┐
│  Frontend BFF（FastAPI · 端口 3000）                      │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │ 文件系统路由  │  │ BFF 业务层    │  │ Jinja2 模板渲染  │   │
│  │ pages/ → URL │  │ @get/@post   │  │ layouts/       │   │
│  │              │  │ 装饰器自注册   │  │ components/    │   │
│  └─────────────┘  └──────┬───────┘  └────────────────┘   │
│                          │ httpx                         │
│                          ▼                               │
│                    BFFBase 基座                            │
│           Token 转发 · contextvars · 模板缓存              │
└──────────────────────────┬───────────────────────────────┘
                           │ Bearer Token
                           ▼
┌──────────────────────────────────────────────────────────┐
│  Backend API（FastAPI · 端口 8012）                      │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ auth     │ │ posts    │ │ users    │ │ friends  │   │
│  │ 注册/登录 │ │ 动态流   │ │ 搜索/详情│ │ 好友请求  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│                                                          │
│  SQLAlchemy ORM ──► SQLite (data.db)                    │
│  JWT 认证        ──► python-jose                         │
└──────────────────────────────────────────────────────────┘
```

**一句话**：两层 FastAPI，一个 SSR 前端，零自定义 JavaScript。

---

## 项目结构

```
PyNuxt-Social/
├── backend/                          # 纯 JSON REST API（独立进程）
│   ├── main.py                       # FastAPI 入口
│   ├── models.py                     # ORM 模型（User, Post, Like, FriendRequest）
│   ├── database.py                   # SQLAlchemy 连接
│   └── routers/                      # API 路由（auth/posts/users/friends）
│
├── frontend/                         # BFF 前端（独立进程）
│   ├── main.py                       # BFF 入口 + Auth 路由 + 文件路由
│   ├── bff_core.py                   # 4 个业务 BFF（Auth/Feed/User/Friend）
│   ├── pynuxt/                       # ★ PyNuxt 框架核心
│   │   ├── __init__.py               #   框架说明 + 版本（v0.5.1）
│   │   ├── bff.py                    #   BFFBase 基座 + 路由自注册装饰器
│   │   ├── routing.py                #   文件系统路由引擎
│   │   ├── templates.py              #   Jinja2 延迟初始化 + 热重载
│   │   ├── auth.py                   #   Cookie/Token 依赖注入
│   │   ├── context.py               #   contextvars 上下文隔离
│   │   ├── errors.py                #   错误处理（401 自动重定向）
│   │   └── middleware.py             #   登录态守卫
│   ├── pages/                        # 页面模板（自动映射 URL）
│   │   ├── index.html               #   GET /
│   │   ├── feed.html                #   GET /feed
│   │   ├── login.html               #   GET /login
│   │   └── users/[username]/         #   动态路由参数
│   ├── components/                   # HTMX 组件模板
│   │   ├── post_item.html           #   帖子片段
│   │   ├── like_button.html         #   点赞按钮
│   │   ├── friend_button.html        #   好友按钮（五态）
│   │   └── ...
│   └── layouts/
│       └── default.html             # 全局布局
│
├── docs/                             # 设计文档
│   ├── class-diagram.mermaid         # 数据库类图
│   └── sequence-diagram.mermaid      # 核心交互时序图
│
├── ARCHITECTURE.md                   # 完整架构设计
├── seed_data.py                      # 种子数据（10用户 × 5帖子）
└── requirements.txt                  # Python 依赖
```

---

## 快速开始

```bash
# 克隆
git clone https://github.com/jeffreyheping/PyNuxt-Social.git
cd PyNuxt-Social

# 安装依赖
pip install -r requirements.txt

# 生成种子数据
python seed_data.py

# 启动后端 API（端口 8012）
cd backend
uvicorn main:app --port 8012 --reload

# 启动前端 BFF（端口 3000，新终端）
cd frontend
uvicorn main:app --port 3000 --reload

# 或者用一键脚本（Windows）
.\start-all.ps1
```

打开 [http://localhost:3000](http://localhost:3000)，注册一个账号，开始体验。

---

## 核心设计

### 文件系统路由

pages/ 目录下的每个 `.html` 文件，启动时自动注册为精确的 GET 路由 —— 不用写任何路由代码：

| 文件路径 | URL |
|---------|-----|
| `pages/index.html` | `GET /` |
| `pages/feed.html` | `GET /feed` |
| `pages/users/[username]/index.html` | `GET /users/{username}` |

这是从 Nuxt.js 学来的核心设计。但实现方式完全不同：Nuxt 在构建时扫描，PyNuxt 在启动时扫描 —— 因为 Python 是运行时语言，不需要"构建"这个步骤。

v0.5.1 的关键改进：**消灭了 catch-all 通配符**。早期版本使用 `/{path:path}` 作为万能路由，会和 BFF 路由冲突（帖子加载 404 就是这么来的）。现在改为启动时精确注册每条路由，和BFF 路由平级共存，零冲突。

### BFF 路由自注册

业务路由用装饰器声明，一行注册：

```python
class FeedBFF(BFFBase):
    prefix = "/bff/posts"

    @get("", auth="optional")
    async def get_posts(self, feed: str = Query("global")):
        posts = await self._get("/api/posts", params={"feed": feed})
        return self._render("components/post_list.html",
                           data=posts,
                           current_user_id=self.current_user_id)

# 一行搞定
FeedBFF.register(app, "http://localhost:8012")
```

四个认证级别：`none` / `token` / `optional` / `required`，在装饰器上声明，框架自动注入依赖。

### 认证传递：contextvars

这是 v0.5.0 最重要的架构改进。

旧版用 `object.__new__()` 克隆 BFF 实例来传递 Token —— 绕过 `__init__`，子类新增属性不会被复制，模式脆弱。v0.5.0 用 Python 的 `contextvars` 替代：

```python
# handler 设置上下文（每个 ASGI 请求天然隔离）
_request_token.set(token)
_request_user_id.set(user_id)

# BFF 方法通过属性读取
@property
def auth_token(self) -> str | None:
    return _request_token.get()
```

零克隆，零 GC 压力，子类自动继承。

### HTMX 交互

所有交互零自定义 JavaScript：

```html
<!-- 发帖 -->
<form hx-post="/bff/posts" hx-target="#post-list">
    <textarea name="content" placeholder="说点什么..." required></textarea>
    <button type="submit">发布</button>
</form>

<!-- 点赞 toggle -->
<button hx-post="/bff/posts/{{ id }}/like"
        hx-target="#like-btn-{{ id }}"
        hx-swap="outerHTML">
    {{ like_count }}
</button>

<!-- 实时搜索 -->
<input hx-get="/bff/users/search"
       hx-trigger="keyup changed delay:300ms"
       hx-target="#search-results">
```

---

## 踩过的坑

一个真实项目比任何文档都有价值的地方在于：**它会告诉你哪些设计是好的，哪些是错的。**

### 坑 1：Catch-all 路由的贪婪性

早期用 `@app.get("/{path:path}")` 做文件系统路由。HTMX 请求 `/bff/posts`（不带尾部斜杠），但 `@get("/")` 注册的是 `/bff/posts/`（带尾部斜杠），请求被 catch-all 截获 → 404。

**教训**：通配符路由是万恶之源。Nuxt 从来没有这个问题，因为 Nuxt 在构建时就精确注册了每条路由。

**修复**：启动时扫描 `pages/` 目录，用 `app.get(route_path)` 逐条精确注册。从此路由和平。

### 坑 2：`inspect.Signature` 的坑

精确注册路由时，自然地写了 `async def handler(request, **path_params)`。结果 FastAPI 把 `path_params` 当成了 query 参数，所有静态页面都返回 422。

**教训**：FastAPI 会用 `inspect.signature()` 解析 handler 参数。`**kwargs` 在它眼里就是 query string。

**修复**：手动构建 `inspect.Signature`，只包含 `Request` 和显式的路径参数名。

### 坑 3：Windows 路径的斜杠问题

`os.path.relpath()` 在 Windows 返回反斜杠 `pages\users\[username]\index.html`，Jinja2 的 `env.get_template()` 找不到文件。

**教训**：Jinja2 的模板路径永远用正斜杠。

**修复**：`.replace("\\", "/")`。一行代码，花了半小时 debug。

### 坑 4：BFFBase 克隆模式

旧版通过 `object.__new__()` 跳过 `__init__` 来克隆 BFF 实例，传递 Token。子类新增属性不参与克隆。

**教训**：不要与 Python 对象模型对抗。`contextvars` 才是 Python 异步上下文传递的正道。

---

## 意义与启示

### 1. Python 全栈不是梦

PyNuxt-Social 证明了一件事：**纯 Python 技术栈完全可以构建一个功能完整的现代 Web 应用**。

- FastAPI 做后端 API —— 性能、异步、类型提示，一个不缺
- FastAPI 做前端 BFF —— 模板渲染、HTTP 代理、Cookie 管理
- Jinja2 做模板 —— 继承、组件、热重载，开发体验不输 Vue
- HTMX 做交互 —— 零 JavaScript 的现代交互

不需要切换语言。不需要 Node.js 构建。不需要 npm 生态。

### 2. SSR 的复兴

HTMX 的流行不是偶然。它代表了一种回归：**让服务器做它最擅长的事 —— 生成 HTML。**

PyNuxt-Social 的前端代码量极少（9 个页面模板 + 9 个组件模板），但实现了完整的社会化功能。对比同功能 React SPA，代码量可能只有 1/3 到 1/5。

### 3. 框架应该从实战中长出来

PyNuxt 的每一行代码都是被 PyNuxt-Social 的真实需求逼出来的：

- **contextvars 替代 clone** → 因为 clone 模式在实战中炸了
- **精确路由替代 catch-all** → 因为帖子加载 404 了
- **共享 httpx 客户端** → 因为每个 BFF 类持一个太浪费
- **模板热重载 + DebugUndefined** → 因为改模板要重启太痛苦

这不是坐在书桌前设计的框架，是站在战场上的框架。

### 4. BFF 模式的普适性

BFF（Backend For Frontend）最初是微服务架构中的概念。但 PyNuxt-Social 展示了它在单体项目中的价值：**职责分离带来的是清晰的边界、独立的测试、和自由的技术选型**。

后端只返回 JSON，理论上可以被任何客户端复用 —— Web、iOS、CLI、甚至另一个 BFF。

### 5. Less is More

这个项目没有用到：
- ❌ React / Vue / Svelte
- ❌ TypeScript
- ❌ Webpack / Vite / esbuild
- ❌ npm / yarn / pnpm
- ❌ Redux / Pinia / Zustand
- ❌ React Query / SWR
- ❌ WebSocket / SSE

它用到的：
- ✅ Python（唯一语言）
- ✅ FastAPI（两个进程）
- ✅ Jinja2（模板）
- ✅ HTMX（交互，一个 .js 文件）
- ✅ SQLAlchemy（ORM）
- ✅ httpx（HTTP 客户端）

有时候，选择不做什么，比选择做什么更重要。

---

## 下一步

PyNuxt-Social 的故事还在继续。框架层的改进路线（详见 `docs/PYNUXT-FRAMEWORK-REVIEW.md`）包括：

- [ ] **P0**: 从 copy-paste 微框架 → 可安装的 pip 包
- [ ] **P0**: 支持子目录 BFF（按业务拆分文件）
- [ ] **P1**: CLI 脚手架（`pynuxt init my-project`）
- [ ] **P1**: 内置 CSRF 防护
- [ ] **P2**: WebSocket 支持
- [ ] **P2**: 管理后台自动生成（基于 ORM 模型）

项目本身也有一系列已知设计缺陷（详见 `ARCHITECTURE.md` 第 10 节），它们是有意的：**每一个缺陷都是下一次迭代的起点。**

---

<p align="center">
  PyNuxt-Social — 用纯 Python 证明全栈 SSR 还活着<br>
  <a href="https://github.com/jeffreyheping/PyNuxt-Social">GitHub</a>
</p>
