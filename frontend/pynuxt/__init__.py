"""
PyNuxt — 纯 Python 全栈 SSR 框架（v0.5.0）

核心理念：零 JavaScript，纯服务端渲染

技术栈：
- FastAPI — Web 框架
- Jinja2 — 模板引擎
- HTMX — 无刷新交互

核心特性：
- 文件系统路由（启动时扫描 pages/，精确注册每条 GET 路由，无 catch-all 冲突）
- BFF 架构（前端业务层，调用后端 API）
- 路由自注册（@get/@post 装饰器 → register() 一行搞定）
- contextvars 认证传递（告别 clone 模式）
- 共享 httpx 客户端（所有 BFF 实例共用一个连接池）
- 请求级用户缓存（同一请求只查一次 /api/auth/me）
- Cookie 认证（零 JS）
- 登录态守卫中间件
- Jinja2 模板缓存（env.get_template() 替代 from_string()）
- 模板热重载（auto_reload + DebugUndefined，开发体验拉满）

用户只写：
- 页面（pages/*.html，需 {% extends %} 声明布局）
- 组件（components/*.html）
- BFF 业务逻辑（bff_core.py，用装饰器声明路由）

框架代码（pynuxt/*）随项目需要持续完善。
"""

__version__ = "0.5.0"
