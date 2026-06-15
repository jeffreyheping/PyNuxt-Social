"""帖子路由 — 动态流 + 发帖 + 点赞

动态流支持 global（全局）和 following（仅关注的人）两种模式。
点赞为 toggle 语义（已赞→取消，未赞→点赞）。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import User, Post, Like, FriendRequest
from routers.auth import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/posts", tags=["posts"])


class PostCreate(BaseModel):
    content: str


# ==================== 工具函数 ====================

def _get_friend_ids(user_id: int, db: Session) -> set:
    """获取某用户的所有好友 ID（accepted 双向）"""
    sent = db.query(FriendRequest).filter(
        FriendRequest.from_user_id == user_id,
        FriendRequest.status == "accepted",
    ).all()
    received = db.query(FriendRequest).filter(
        FriendRequest.to_user_id == user_id,
        FriendRequest.status == "accepted",
    ).all()

    friend_ids = set()
    for fr in sent:
        friend_ids.add(fr.to_user_id)
    for fr in received:
        friend_ids.add(fr.from_user_id)
    return friend_ids


def _serialize_post_fast(
    post: Post,
    authors: dict[int, User],
    likes_by_post: dict[int, list[Like]],
    current_user_id: int | None,
) -> dict:
    """将 Post ORM 对象序列化为 API 响应字典（使用预取数据，零额外查询）"""
    author = authors.get(post.author_id)
    post_likes = likes_by_post.get(post.id, [])
    like_count = len(post_likes)
    liked_by_me = any(l.user_id == current_user_id for l in post_likes) if current_user_id else False

    return {
        "id": post.id,
        "author": {
            "id": author.id,
            "username": author.username,
            "display_name": author.display_name,
        } if author else None,
        "content": post.content,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "like_count": like_count,
        "liked_by_me": liked_by_me,
    }


def _batch_serialize_posts(
    posts: list[Post],
    db: Session,
    current_user_id: int | None,
) -> list[dict]:
    """批量序列化帖子列表（3 SQL 固定，无论帖子数量）"""
    if not posts:
        return []

    # SQL 1: 批量查询作者
    author_ids = {p.author_id for p in posts}
    authors = {u.id: u for u in db.query(User).filter(User.id.in_(author_ids)).all()}

    # SQL 2: 批量查询点赞
    post_ids = [p.id for p in posts]
    likes = db.query(Like).filter(Like.post_id.in_(post_ids)).all()

    # 按 post_id 分组
    likes_by_post: dict[int, list[Like]] = {}
    for like in likes:
        likes_by_post.setdefault(like.post_id, []).append(like)

    return [_serialize_post_fast(p, authors, likes_by_post, current_user_id) for p in posts]


# ==================== API 路由 ====================

@router.get("")
def get_posts(
    feed: str = Query("global"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """获取动态流

    feed=global: 所有人帖子
    feed=following: 仅好友帖子（需登录）
    """
    if feed == "following":
        if not current_user:
            raise HTTPException(status_code=401, detail="查看关注流需要登录")
        friend_ids = _get_friend_ids(current_user.id, db)
        if not friend_ids:
            return []
        posts = (
            db.query(Post)
            .filter(Post.author_id.in_(friend_ids))
            .order_by(Post.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    else:
        posts = (
            db.query(Post)
            .order_by(Post.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    return _batch_serialize_posts(posts, db, current_user.id if current_user else None)


@router.post("", status_code=201)
def create_post(
    post_in: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建帖子（需登录，280 字限制）"""
    if not post_in.content or not post_in.content.strip():
        raise HTTPException(status_code=422, detail="内容不能为空")
    if len(post_in.content) > 280:
        raise HTTPException(status_code=422, detail="内容不能超过280字")

    post = Post(content=post_in.content.strip(), author_id=current_user.id)
    db.add(post)
    db.commit()
    db.refresh(post)

    return {
        "id": post.id,
        "author": {
            "id": current_user.id,
            "username": current_user.username,
            "display_name": current_user.display_name,
        },
        "content": post.content,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "like_count": 0,
        "liked_by_me": False,
    }


@router.post("/{post_id}/like")
def toggle_like(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """点赞 / 取消赞（toggle 语义）"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    existing = db.query(Like).filter(
        Like.user_id == current_user.id, Like.post_id == post_id
    ).first()

    if existing:
        # 已赞 → 取消
        db.delete(existing)
        db.commit()
        like_count = db.query(Like).filter(Like.post_id == post_id).count()
        return {"liked": False, "like_count": like_count}
    else:
        # 未赞 → 点赞
        like = Like(user_id=current_user.id, post_id=post_id)
        db.add(like)
        db.commit()
        like_count = db.query(Like).filter(Like.post_id == post_id).count()
        return {"liked": True, "like_count": like_count}
