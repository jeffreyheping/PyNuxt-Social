"""用户路由 — 搜索 / 详情 / 帖子 / 粉丝 / 关注

好友关系是双向的（accepted），所以 followers 和 following 实际返回同一批人。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import User, Post, Like, FriendRequest
from routers.auth import get_current_user_optional
from routers.posts import _serialize_post, _get_friend_ids

router = APIRouter(prefix="/api/users", tags=["users"])


# ==================== API 路由 ====================

@router.get("")
def search_users(
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """搜索用户（按 username / display_name 模糊匹配）"""
    if not q:
        return []
    users = (
        db.query(User)
        .filter((User.username.contains(q)) | (User.display_name.contains(q)))
        .limit(20)
        .all()
    )
    return [
        {
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.get("/{username}")
def get_user(username: str, db: Session = Depends(get_db)):
    """获取用户详情（含统计）"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    post_count = db.query(Post).filter(Post.author_id == user.id).count()

    # 好友数（accepted 双向）
    friend_count = db.query(FriendRequest).filter(
        FriendRequest.status == "accepted",
        (FriendRequest.from_user_id == user.id) | (FriendRequest.to_user_id == user.id),
    ).count()

    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "post_count": post_count,
        "follower_count": friend_count,
        "following_count": friend_count,
    }


@router.get("/{username}/posts")
def get_user_posts(
    username: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """获取某用户的帖子列表"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    posts = (
        db.query(Post)
        .filter(Post.author_id == user.id)
        .order_by(Post.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_serialize_post(p, current_user, db) for p in posts]


@router.get("/{username}/followers")
def get_followers(username: str, db: Session = Depends(get_db)):
    """获取粉丝列表（双向好友 = 互相关注，粉丝即好友）"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    friend_ids = _get_friend_ids(user.id, db)
    if not friend_ids:
        return []

    followers = db.query(User).filter(User.id.in_(friend_ids)).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in followers
    ]


@router.get("/{username}/following")
def get_following(username: str, db: Session = Depends(get_db)):
    """获取关注列表（双向好友 = 互相关注，关注即好友）"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    friend_ids = _get_friend_ids(user.id, db)
    if not friend_ids:
        return []

    following = db.query(User).filter(User.id.in_(friend_ids)).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in following
    ]
