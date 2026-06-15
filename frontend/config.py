"""前端配置 — 等同 Nuxt nuxt.config.ts"""
import os

# 开发模式（True = 显示详细错误信息，False = 友好提示）
DEBUG = True

# 后端 API 地址
API_BASE = os.getenv("API_BASE", "http://localhost:8012")

# 站点名称
SITE_NAME = "PyNuxt-Social"

# 前端服务端口
PORT = 3000

# 页面目录（文件系统路由：/about -> pages/about.html）
PAGES_DIR = "pages"

# 模板根目录（Jinja2 FileSystemLoader 根）
TEMPLATE_DIRS = [".", "static/js"]

# 需要登录才能访问的路径前缀
PROTECTED_PATHS = ["/feed", "/friends", "/search", "/users"]

# 登录页路径
LOGIN_PATH = "/login"

# Cookie 配置
AUTH_COOKIE_NAME = "auth_token"
AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 天
