"""好友关系路由 — 三态状态机

none → pending → accepted / rejected

状态说明：
- none: 无关系
- pending: 已发送请求（等待对方处理）
- pending_received: 对方发来的请求（待我处理）
- accepted: 已是好友
- rejected: 被拒绝（允许重新发送）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import User, FriendRequest
from routers.auth import get_current_user

router = APIRouter(prefix="/api/friends", tags=["friends"])


class FriendAction(BaseModel):
    action: str  # accept | reject


# ==================== API 路由 ====================

@router.get("/requests")
def get_pending_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取待处理好友请求（发给我的、状态为 pending）"""
    requests = (
        db.query(FriendRequest)
        .filter(
            FriendRequest.to_user_id == current_user.id,
            FriendRequest.status == "pending",
        )
        .order_by(FriendRequest.created_at.desc())
        .all()
    )

    result = []
    for fr in requests:
        from_user = db.query(User).filter(User.id == fr.from_user_id).first()
        result.append({
            "id": fr.id,
            "from_user": {
                "id": from_user.id,
                "username": from_user.username,
                "display_name": from_user.display_name,
            } if from_user else None,
            "status": fr.status,
            "created_at": fr.created_at.isoformat() if fr.created_at else None,
        })
    return result


@router.post("/requests/{username}", status_code=201)
def send_request(
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发送好友请求"""
    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise HTTPException(status_code=404, detail="目标用户不存在")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能向自己发送好友请求")

    # 查找已有记录（任一方向）
    existing = db.query(FriendRequest).filter(
        (
            (FriendRequest.from_user_id == current_user.id)
            & (FriendRequest.to_user_id == target.id)
        )
        | (
            (FriendRequest.from_user_id == target.id)
            & (FriendRequest.to_user_id == current_user.id)
        )
    ).first()

    if existing:
        if existing.status == "accepted":
            raise HTTPException(status_code=400, detail="已是好友")
        if existing.status == "pending":
            if existing.from_user_id == current_user.id:
                raise HTTPException(status_code=400, detail="已发送过好友请求")
            else:
                raise HTTPException(status_code=400, detail="对方已向你发送好友请求，请去处理")
        if existing.status == "rejected":
            # 允许重新发送：更新原记录
            existing.status = "pending"
            existing.from_user_id = current_user.id
            existing.to_user_id = target.id
            db.commit()
            db.refresh(existing)
            return {
                "id": existing.id,
                "from_user_id": current_user.id,
                "to_user_id": target.id,
                "status": existing.status,
                "created_at": existing.created_at.isoformat() if existing.created_at else None,
            }

    # 新建请求
    fr = FriendRequest(from_user_id=current_user.id, to_user_id=target.id, status="pending")
    db.add(fr)
    db.commit()
    db.refresh(fr)

    return {
        "id": fr.id,
        "from_user_id": current_user.id,
        "to_user_id": target.id,
        "status": fr.status,
        "created_at": fr.created_at.isoformat() if fr.created_at else None,
    }


@router.put("/requests/{request_id}")
def respond_request(
    request_id: int,
    action: FriendAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """接受 / 拒绝好友请求"""
    fr = db.query(FriendRequest).filter(FriendRequest.id == request_id).first()
    if not fr:
        raise HTTPException(status_code=404, detail="请求不存在")
    if fr.to_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能处理发给自己的请求")
    if fr.status != "pending":
        raise HTTPException(status_code=400, detail="该请求已处理")
    if action.action not in ("accept", "reject"):
        raise HTTPException(status_code=400, detail="action 必须是 accept 或 reject")

    fr.status = "accepted" if action.action == "accept" else "rejected"
    db.commit()
    db.refresh(fr)

    return {"id": fr.id, "status": fr.status}


@router.get("/status/{username}")
def get_friend_status(
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取与目标用户的好友关系状态

    返回：self | none | pending | pending_received | accepted | rejected
    """
    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.id == current_user.id:
        return {"status": "self"}

    fr = db.query(FriendRequest).filter(
        (
            (FriendRequest.from_user_id == current_user.id)
            & (FriendRequest.to_user_id == target.id)
        )
        | (
            (FriendRequest.from_user_id == target.id)
            & (FriendRequest.to_user_id == current_user.id)
        )
    ).first()

    if not fr:
        return {"status": "none"}

    if fr.status == "accepted":
        return {"status": "accepted"}

    if fr.status == "rejected":
        # 被拒绝后，只有发送方看到 rejected，接收方看到 none
        if fr.from_user_id == current_user.id:
            return {"status": "rejected"}
        return {"status": "none"}

    # pending：区分是"我发的"还是"收到的"
    if fr.from_user_id == current_user.id:
        return {"status": "pending"}
    return {"status": "pending_received"}
