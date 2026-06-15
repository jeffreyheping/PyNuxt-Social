# PyNuxt-Social 前端改进计划

当前版本：v0.5.x
目标版本：v0.6
文档日期：2025

---

## 一、架构层面改进（高优先级）

### 1.1 统一 HTTP 客户端单例

**问题**：
- `pynuxt/auth.py` 中 `_shared_client` 是一个独立的 httpx.AsyncClient
- `pynuxt/bff.py` 中 `BFFBase._shared_client` 是另一个独立的 httpx.AsyncClient
- 两者都是调用同一个后端 API，但各自维护连接池，浪费资源

**影响**：
- 两个独立连接池 → 更多 TCP 连接开销
- 两个独立超时/重试配置 → 行为可能不一致
- 关闭时只关了 BFF 的客户端 → auth 客户端可能泄漏

**改进方案**：
```python
# pynuxt/http.py（新增）
_shared_client: httpx.AsyncClient | None = None

def get_client(api_base: str = None) -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            base_url=api_base or "",
            timeout=10.0,
        )
    return _shared_client

async def close_client():
    global _shared_client
    if _shared_client and not _shared_client.is_closed:
        await _shared_client.aclose()
        _shared_client = None
```

在 `auth.py` 和 `bff.py` 中都使用这个统一的客户端。

---

### 1.2 统一认证配置管理

**问题**：
- `config.py` 中 `AUTH_COOKIE_NAME`、`AUTH_COOKIE_MAX_AGE` 是写死的
- `main.py` 中 `_set_auth_cookie` 硬编码 `httponly=True, samesite="lax", path="/"`
- 缺少 `Secure` 属性（HTTPS 时应该启用）
- 缺少 Cookie 过期时间的人性化处理

**改进方案**：
1. `config.py` 增加完整的 Cookie 配置：
```python
AUTH_COOKIE_CONFIG = {
    "name": "auth_token",
    "max_age": 60 * 60 * 24 * 7,  # 7 天
    "httponly": True,
    "samesite": "lax",
    "path": "/",
    "secure": False,  # 生产环境 HTTPS 时设为 True
}
```

2. `main.py` 使用配置而非硬编码：
```python
from config import AUTH_COOKIE_CONFIG

def _set_auth_cookie(response: Response, token: str) -> Response:
    response.set_cookie(
        key=AUTH_COOKIE_CONFIG["name"],
        value=token,
        httponly=AUTH_COOKIE_CONFIG["httponly"],
        samesite=AUTH_COOKIE_CONFIG["samesite"],
        path=AUTH_COOKIE_CONFIG["path"],
        max_age=AUTH_COOKIE_CONFIG["max_age"],
        secure=AUTH_COOKIE_CONFIG["secure"],
    )
    return response
```

---

### 1.3 统一 BFF 路由注册方式

**问题**：
- AuthBFF 的 login/register/logout 路由在 `main.py` 手动注册，使用 `@app.post`
- FeedBFF、UserBFF、FriendBFF 使用 `BFFBase.register()` 自动注册
- 两种模式并存，不利于维护

**原因**：AuthBFF 需要操作 Response（设置/删除 Cookie），而 BFFBase 目前只支持返回 HTML 字符串

**改进方案**：在 `BFFBase` 中增加 `@route` 装饰器对 `Response` 对象的原生支持，让 AuthBFF 也可以用装饰器声明路由。

---

### 1.4 统一版本号

**问题**：
- `pynuxt/__init__.py` 写的是 `__version__ = "0.5.0"`
- 其他文件（routing.py、templates.py）注释写的是 "v0.5.1"

**改进**：统一为 0.5.x（实际版本由 issues.md 管理）

---

### 1.5 缺少 CSRF 保护（安全高优先级）

**问题**：
- HTMX 表单提交没有 CSRF token 校验
- 虽然是 Cookie+httponly，但缺少 CSRF 保护是安全隐患

**改进方案**：
1. 页面渲染时注入 CSRF token（存在 session 或 带签名的 Cookie）
2. HTMX 自动携带：`hx-vals` 或 `hx-headers`
3. BFF 层校验 token

参考：`frontend-flet/` 中的实现（如果有的话）

---

## 二、代码层面改进（中优先级）

### 2.1 统一日期格式化

**问题**：
- 多个地方用 `[:16]` 硬截断日期字符串：
  - `components/post_item.html`: `{{ post.created_at[:16] }}`
  - `components/friend_request_list.html`: `{{ req.created_at[:16] }}`
- 格式不一致（依赖后端返回格式）
- 如果后端返回 None，模板会崩溃（有保护但不够优雅）

**改进方案**：
1. 在 `pynuxt/templates.py` 注册 Jinja2 自定义 filter：
```python
from datetime import datetime

def format_datetime(value: str, fmt: str = "%Y-%m-%d %H:%M") -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime(fmt)
    except (ValueError, AttributeError):
        return str(value)[:16] if value else ""

def time_ago(value: str) -> str:
    """人性化时间显示：3分钟前、2小时前、1天前"""
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        delta = now - dt
        seconds = delta.total_seconds()
        if seconds < 60:
            return f"{int(seconds)}秒前"
        elif seconds < 3600:
            return f"{int(seconds // 60)}分钟前"
        elif seconds < 86400:
            return f"{int(seconds // 3600)}小时前"
        elif seconds < 604800:
            return f"{int(seconds // 86400)}天前"
        else:
            return format_datetime(value, "%Y-%m-%d")
    except (ValueError, AttributeError):
        return str(value)[:16] if value else ""

# 在 _ensure_env() 中注册：
env.filters["datetime"] = format_datetime
env.filters["time_ago"] = time_ago
```

2. 模板中改用：
```html
<span class="post-time">{{ post.created_at|time_ago }}</span>
```

---

### 2.2 移除模板中硬编码的内联样式

**问题**：`components/friend_button.html` 中：
```html
<span class="btn btn-sm" style="background:#fff3e0;color:#e65100;border-color:#ffe0b2;">已申请...</span>
<span class="btn btn-sm" style="background:#e3f2fd;color:#1565c0;border-color:#bbdefb;">待你处理</span>
```

硬编码颜色违反了 "样式/结构分离"，不利于后续换主题/换色方案。

**改进方案**：在 `style.css` 增加状态类：
```css
.btn-status-pending {
    background: #fff3e0;
    color: #e65100;
    border-color: #ffe0b2;
}

.btn-status-pending-received {
    background: #e3f2fd;
    color: #1565c0;
    border-color: #bbdefb;
}
```

模板改为：
```html
<span class="btn btn-sm btn-status-pending">已申请...</span>
<span class="btn btn-sm btn-status-pending-received">待你处理</span>
```

---

### 2.3 统一模板数据传递模式

**问题**：BFF 返回数据给模板时，有的地方用 `data.xxx`，有的地方直接展开：
- `components/feed_content.html`: 直接用 `{{ current_feed }}`（模板上下文注入）
- `components/post_list.html`: `{% for post in data %}`
- `components/profile_header.html`: `{{ data.display_name }}`
- `components/user_card.html`: 需要检查

**改进方案**：统一为"模板明确声明需要哪些字段"，BFF 层明确传递这些字段。建议约定：
- 列表渲染用 `data`（如帖子列表、请求列表）
- 单对象渲染直接展开到顶层（如 profile_header）

---

### 2.4 统一 HTMX 错误处理

**问题**：
- 很多 HTMX 请求如果失败（422、500 等），没有错误反馈
- `login.html` 只有一个 `#auth-message` 容器，错误样式简陋
- 发帖失败时用户看不到任何提示

**改进方案**：
1. 在 `style.css` 增加 HTMX 错误样式：
```css
.htmx-error {
    background: #ffebee;
    color: #c62828;
    padding: 10px 16px;
    border-radius: 6px;
    margin-bottom: 10px;
    font-size: 14px;
    animation: slideIn 0.2s ease;
}

@keyframes slideIn {
    from { opacity: 0; transform: translateY(-5px); }
    to { opacity: 1; transform: translateY(0); }
}
```

2. 增加全局 HTMX 错误钩子（在 `layouts/default.html`）：
```html
<script>
document.body.addEventListener('htmx:responseError', function(evt) {
    // 对所有 HTMX 失败请求添加闪烁提示
});
</script>
```

---

## 三、功能层面改进（按优先级排序）

### 3.1 加载状态与 Loading 指示器（中优先级）

**问题**：
- 发帖时按钮没有 disabled/loading 状态 → 用户可能重复提交
- Tab 切换时"关注"如果没有帖子，用户可能不知道是加载中还是真的为空
- 用户主页初始加载时两个独立区域同时显示"加载中..."

**改进方案**：
1. 发帖按钮增加 loading 状态：
```html
<button type="submit" class="btn btn-primary"
        :disabled="!content.trim()"
        hx-indicator="#post-loading">
    <span id="post-loading" class="htmx-indicator">发布中...</span>
    <span hx-history="false">发布</span>
</button>
```

2. 在 `style.css` 增加 HTMX indicator 样式：
```css
.htmx-indicator {
    display: none;
}
.htmx-request .htmx-indicator {
    display: inline;
}
.htmx-request .btn-primary .htmx-indicator + span {
    display: none;
}
```

---

### 3.2 分页 / 无限滚动（中优先级）

**问题**：
- 帖子列表一次性加载，没有分页
- `skip` / `limit` 参数已存在于 BFF 层 `get_posts` 中，但前端没用到
- 帖子多了之后首屏加载慢

**改进方案**：
- 增加"加载更多"按钮或滚动加载（HTMX `reveal` trigger）
- 组件参考：
```html
{# 追加到 post_list.html 底部 #}
{% if data|length >= 20 %}
<div id="load-more"
     hx-get="/bff/posts?feed={{ current_feed }}&skip={{ next_skip }}&limit=20"
     hx-trigger="revealed"
     hx-swap="outerHTML">
    <button class="btn btn-block">加载更多</button>
</div>
{% endif %}
```

需要 BFF 层返回 `next_skip` 或类似信息。

---

### 3.3 帖子删除/编辑功能（低优先级）

当前没有：用户发了帖子后无法删除或编辑。

**设计**：
- 帖子作者在 `post_item.html` 中看到"编辑/删除"按钮
- 编辑：用 HTMX 把内容换成可编辑 `<textarea>`
- 删除：点击后确认对话框，然后调后端 DELETE API

---

### 3.4 评论系统（低优先级）

当前只有帖子+点赞，没有评论。

**设计**：参考 Facebook/Twitter：
- 每条帖子底部"评论"按钮（计数）
- 点击展开评论输入框 + 评论列表
- 评论使用独立的 BFF 路由（`/bff/posts/{id}/comments`）

---

### 3.5 用户资料编辑（低优先级）

当前用户主页（`/users/{username}`）只有展示，没有编辑入口。

**设计**：
- 自己的主页增加"编辑资料"按钮
- 点击弹出编辑表单（HTMX partial）
- 可编辑：昵称、头像、个人简介

---

### 3.6 通知/消息系统（低优先级）

**设计**：
- 导航栏增加"通知"图标 + 未读数（类似 Bell 图标）
- 新的好友请求、有人点赞你、有人关注你 等事件都进通知

---

### 3.7 图片上传（低优先级）

当前发帖只有纯文本。

**设计**：
- 发帖框增加图片上传按钮（`<input type="file">`）
- 后端存储到本地或对象存储
- 帖子渲染时展示图片

---

## 四、UX/UI 改进（中/低优先级）

### 4.1 统一空状态设计

**问题**：多个地方用类似但不完全一样的"暂无xxx"文案：
- `post_list.html`: "暂无动态"
- `friend_request_list.html`: "暂无待处理请求"
- `search.html`（初始）: "输入关键词搜索用户"

**改进方案**：抽出统一的空状态组件，并支持 emoji 图标。

---

### 4.2 Tab 切换的平滑体验

**问题**：
- 当前 Tab 切换有闪烁（HTMX 加载列表时容器会短暂空白）
- 没有 skeleton loading 占位

**改进方案**：
- HTMX 加载期间显示骨架屏 CSS 占位
- `hx-indicator` 配合局部 loading

---

### 4.3 移动端响应式优化

**现状**：
- 容器 `max-width: 680px` 对桌面端偏小
- 导航栏在窄屏时链接可能溢出
- 缺少 mobile-first 思路

**改进**：
- `@media` 查询增加移动端优化
- 导航栏汉堡菜单

---

### 4.4 键盘快捷键

**建议**：
- `Ctrl/Cmd + Enter` 在发帖框中直接提交
- `/` 聚焦搜索框

---

## 五、安全改进（高优先级）

### 5.1 密码强度校验（前端+后端）

**问题**：当前只有 HTML `minlength="6"`，这只是浏览器层的提示，缺乏真正校验。

**改进**：
- 注册页面用 Alpine.js 做即时强度提示（弱/中/强）
- BFF 层增加密码校验（长度、字符多样性）

---

### 5.2 XSS 防护检查

**检查点**：
- 帖子内容渲染用 `{{ post.content }}`，如果用户输入 HTML 会怎样？
- Jinja2 有 `autoescape` 全局开启（在 `templates.py`），默认应该安全
- 但要特别检查：如果未来有 Markdown/富文本渲染，需要严格 sanitize

---

### 5.3 用户名/邮箱唯一性校验提示

**问题**：注册失败时返回 "注册失败，用户名或邮箱可能已存在" 但没有高亮指出是哪个。

**改进**：BFF 层返回结构化错误信息（字段级别），前端对应高亮。

---

## 六、性能优化

### 6.1 首屏请求瀑布流

**问题**：
- 用户主页（`/users/{username}`）至少触发 3 个独立 HTMX 请求：
  1. profile header
  2. 帖子列表
  3. 好友关系按钮
- 都是串行等待

**改进**：
- 直接在页面渲染时同步返回 profile header 数据（不需要 hx-get 延迟加载）
- 如果后端 API 性能足够（本地 SQLite 应该很快），可以把用户主页改为一次请求返回完整 HTML

---

### 6.2 静态资源缓存

**改进**：为 `/static` 文件增加 HTTP 缓存头（FastAPI 中 `StaticFiles` 已支持，可用中间件加 `Cache-Control`）

---

### 6.3 减少 HTTP 往返

**问题**：feed.html 首屏后，又触发一次 HTMX 请求完整 feed_content。实际上 BFF 可以直接在页面渲染时返回数据。

**改进**：feed.html 页面渲染时就带上初始数据，不需要首屏再 hx-get 一次。

---

## 七、代码组织建议

### 7.1 建议的目录结构

```
frontend/
├── main.py                    # 入口（不变）
├── config.py                  # 配置（不变，增加 CSRF/Cookie 完整配置）
├── bff_core.py               # 业务 BFF（不变）
├── pynuxt/                   # 框架核心（不变）
│   ├── __init__.py
│   ├── auth.py               # 认证工具（优化：统一 httpx 客户端）
│   ├── bff.py                # BFF 基座（不变）
│   ├── routing.py            # 文件系统路由（不变）
│   ├── templates.py          # 模板环境（优化：增加 date filters）
│   ├── middleware.py         # 中间件（不变）
│   ├── errors.py             # 错误处理（不变）
│   ├── context.py            # contextvars（不变）
│   └── http.py               # 【新增】统一 httpx 客户端
├── layouts/                  # 布局模板
│   └── default.html           # （优化：全局 HTMX error hook）
├── pages/                    # 页面（不变）
├── components/               # 组件
│   ├── auth_*.html
│   ├── post_*.html
│   ├── feed_*.html
│   ├── user_*.html
│   ├── friend_*.html
│   ├── search_*.html
│   └── shared/               # 【新增】共享组件（空状态、loading 等）
└── static/
    ├── css/
    │   └── style.css          # （优化：移除内联样式依赖）
    └── js/
        ├── htmx.min.js        # （不变）
        └── alpine.min.js      # （不变）
```

---

## 八、优先执行顺序

### Phase 1（立刻做，高价值低风险）
1. **统一 httpx 客户端**（新增 `pynuxt/http.py`）
2. **统一 Cookie 配置**（完善 `config.py`）
3. **日期格式化 filter**（`pynuxt/templates.py` + CSS 无改动）
4. **版本号统一**（一行改动）

### Phase 2（可以分开发分支做）
5. **移除内联样式**（friend_button.html + CSS）
6. **Loading 指示器**（CSS + feed_content.html）
7. **全局 HTMX 错误提示**（CSS + default.html）

### Phase 3（需要后端配合的新功能）
8. **分页/无限滚动**
9. **帖子编辑/删除**
10. **评论系统**
11. **用户资料编辑**

### Phase 4（锦上添花）
12. **通知系统**
13. **图片上传**
14. **移动端优化**
15. **键盘快捷键**
16. **CSRF 保护**

---

## 九、测试清单

改进后应验证：
- [ ] 登录/注册/登出流程正常
- [ ] 发帖/点赞/取消点赞正常
- [ ] 加好友/接受/拒绝正常
- [ ] 搜索用户正常
- [ ] 用户主页正常
- [ ] Tab 切换正常（全局/关注）
- [ ] 日期格式：新帖子显示"xx分钟前"，旧帖子显示日期
- [ ] 错误时能看到红色提示条
- [ ] 发帖期间按钮自动 disabled
- [ ] 各种空状态正常显示
- [ ] 移动端布局正常（<768px 宽度）
- [ ] 未登录访问受保护页面自动跳回登录
- [ ] CSRF 保护工作正常（如果实现了）

---

## 十、参考资料

- HTMX 文档: https://htmx.org/docs/
- Alpine.js 文档: https://alpinejs.dev/
- Jinja2 文档: https://jinja.palletsprojects.com/
- FastAPI 文档: https://fastapi.tiangolo.com/
