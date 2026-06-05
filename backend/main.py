"""FastAPI 后端入口

纯 JSON REST API，可供多端复用（Web/移动/桌面）。
不感知前端，不做模板渲染。
"""
from fastapi import FastAPI

from database import engine, Base
from routers import auth, users, posts, friends

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="PyNuxt-Social API", version="1.0.0")

# 注册路由
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(friends.router)


@app.get("/")
def root():
    """根路径 - API 信息"""
    return {
        "message": "PyNuxt-Social API",
        "docs": "/docs",
        "endpoints": {
            "auth": "/api/auth",
            "users": "/api/users",
            "posts": "/api/posts",
            "friends": "/api/friends",
        },
    }
