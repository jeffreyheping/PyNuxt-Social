"""SQLAlchemy 数据模型

4 张表：User / Post / Like / FriendRequest
好友关系通过 FriendRequest(status=accepted) 双向判定，无独立 Follow 表。
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 反向引用
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    sent_requests = relationship(
        "FriendRequest", foreign_keys="FriendRequest.from_user_id",
        back_populates="from_user", cascade="all, delete-orphan"
    )
    received_requests = relationship(
        "FriendRequest", foreign_keys="FriendRequest.to_user_id",
        back_populates="to_user", cascade="all, delete-orphan"
    )


class Post(Base):
    """帖子模型（280 字限制）"""
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(String(280), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    author = relationship("User", back_populates="posts")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")


class Like(Base):
    """点赞模型（user_id + post_id 唯一约束 → toggle 语义）"""
    __tablename__ = "likes"
    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="uq_like_user_post"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)

    user = relationship("User")
    post = relationship("Post", back_populates="likes")


class FriendRequest(Base):
    """好友请求模型

    状态机：none → pending → accepted / rejected
    accepted = 双向关注（无独立 Follow 表）
    UNIQUE(from_user_id, to_user_id) 防止重复请求
    """
    __tablename__ = "friend_requests"
    __table_args__ = (
        UniqueConstraint("from_user_id", "to_user_id", name="uq_friend_request"),
        Index("ix_friend_request_to_status", "to_user_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")  # pending | accepted | rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    from_user = relationship("User", foreign_keys=[from_user_id], back_populates="sent_requests")
    to_user = relationship("User", foreign_keys=[to_user_id], back_populates="received_requests")
