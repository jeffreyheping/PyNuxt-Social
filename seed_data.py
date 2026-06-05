"""种子数据脚本

创建 10 个用户 × 5 条帖子 + 好友关系 + 点赞数据。
测试账号: user01~user10, 密码: password123
"""
import sys
import os

# 添加 backend 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from database import engine, SessionLocal, Base
from models import User, Post, Like, FriendRequest
from routers.auth import get_password_hash

# 确保表已创建
Base.metadata.create_all(bind=engine)


def seed():
    """填充种子数据"""
    db = SessionLocal()
    try:
        # 清空数据（按依赖顺序）
        db.query(Like).delete()
        db.query(FriendRequest).delete()
        db.query(Post).delete()
        db.query(User).delete()
        db.commit()

        # 创建 10 个用户
        display_names = [
            "张三", "李四", "王五", "赵六", "钱七",
            "孙八", "周九", "吴十", "郑冬", "冯春"
        ]
        users = []
        for i in range(1, 11):
            username = f"user{i:02d}"
            user = User(
                username=username,
                email=f"{username}@example.com",
                display_name=display_names[i - 1],
                password_hash=get_password_hash("password123"),
            )
            db.add(user)
            users.append(user)
        db.commit()

        # 刷新获取 ID
        for u in users:
            db.refresh(u)

        # 每用户 5 条帖子
        post_contents = [
            "今天天气真好！",
            "学习 FastAPI 中...",
            "Python 真不错！",
            "HTMX 太酷了！",
            "纯 SSR 也能做社交！",
        ]
        for user in users:
            for content in post_contents:
                post = Post(
                    content=f"[{user.display_name}] {content}",
                    author_id=user.id,
                )
                db.add(post)
        db.commit()

        # 好友关系：user01↔user02, user01↔user03, user02↔user03 (accepted)
        friend_pairs = [(0, 1), (0, 2), (1, 2)]
        for from_idx, to_idx in friend_pairs:
            fr = FriendRequest(
                from_user_id=users[from_idx].id,
                to_user_id=users[to_idx].id,
                status="accepted",
            )
            db.add(fr)

        # user04 → user01 (pending，待处理)
        fr = FriendRequest(
            from_user_id=users[3].id,
            to_user_id=users[0].id,
            status="pending",
        )
        db.add(fr)
        db.commit()

        # 点赞数据：随机给前 10 条帖子点赞
        all_posts = db.query(Post).all()
        for user in users[:5]:
            for post in all_posts[:10]:
                if post.author_id != user.id and hash(f"{user.id}-{post.id}") % 3 == 0:
                    like = Like(user_id=user.id, post_id=post.id)
                    db.add(like)
        db.commit()

        import sys
        sys.stdout.reconfigure(encoding='utf-8')
        print("[OK] 种子数据创建完成！")
        print(f"   用户: {len(users)}")
        print(f"   帖子: {db.query(Post).count()}")
        print(f"   好友关系: {db.query(FriendRequest).count()}")
        print(f"   点赞: {db.query(Like).count()}")
        print("\n测试账号: user01~user10, 密码: password123")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
