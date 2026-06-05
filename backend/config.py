"""后端应用配置"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)  # backend/ → PyNuxt-Social/
DB_PATH = os.path.join(ROOT_DIR, "data.db")

# SQLAlchemy 连接 URI
DB_URI = f"sqlite:///{DB_PATH}"

# JWT 配置
JWT_SECRET = os.getenv("JWT_SECRET", "pynuxt-social-dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 天
