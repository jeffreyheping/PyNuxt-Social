"""数据库连接管理

使用 SQLAlchemy + SQLite，yield 模式依赖注入。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import DB_URI

# 创建引擎（SQLite 需要关闭同线程检查）
engine = create_engine(DB_URI, connect_args={"check_same_thread": False})

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 模型基类
Base = declarative_base()


def get_db():
    """依赖注入：获取数据库会话（yield 模式，自动关闭）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
