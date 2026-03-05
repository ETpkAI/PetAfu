from __future__ import annotations
from typing import Optional, List
"""
社区"宠友圈" API
- 发帖（图文）
- 分页列表
- 点赞/取消
- 评论
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from app.core.database import get_db
from app.models.models import CommunityPost, PostLike, PostComment, User
from app.api.users import get_current_user
from app.services.storage_service import save_upload

router = APIRouter(prefix="/community", tags=["community"])


# ── 响应模型 ──

class AuthorOut(BaseModel):
    id: int
    nickname: Optional[str]
    avatar_url: Optional[str]


class CommentOut(BaseModel):
    id: int
    author: AuthorOut
    content: str
    created_at: datetime


class PostOut(BaseModel):
    id: int
    author: AuthorOut
    content: str
    images: List[str]
    like_count: int
    comment_count: int
    liked_by_me: bool
    created_at: datetime


# ── 发帖 ──

@router.post("/posts", status_code=201)
async def create_post(
    content: str = Form(..., description="帖子文字内容"),
    images: List[UploadFile] = File(default=[], description="帖子图片（最多9张）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not content.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")
    if len(images) > 9:
        raise HTTPException(status_code=400, detail="最多上传9张图片")

    # 保存图片
    image_urls = []
    for img in images:
        if img.filename:  # 过滤空文件
            try:
                url = await save_upload(img, sub_dir="community")
                image_urls.append(url)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

    post = CommunityPost(
        author_id=current_user.id,
        content=content.strip(),
        images_json=json.dumps(image_urls) if image_urls else None,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)

    return _post_to_dict(post, current_user, liked=False)


# ── 帖子列表（分页） ──

@router.get("/posts")
async def list_posts(
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * size

    # 查帖子 + 作者
    result = await db.execute(
        select(CommunityPost)
        .order_by(desc(CommunityPost.created_at))
        .offset(offset)
        .limit(size)
    )
    posts = result.scalars().all()

    # 批量查当前用户是否点赞
    post_ids = [p.id for p in posts]
    liked_set = set()
    if post_ids:
        like_result = await db.execute(
            select(PostLike.post_id).where(
                and_(
                    PostLike.post_id.in_(post_ids),
                    PostLike.user_id == current_user.id,
                )
            )
        )
        liked_set = set(like_result.scalars().all())

    # 加载作者信息
    author_ids = list(set(p.author_id for p in posts))
    authors_map = {}
    if author_ids:
        authors_result = await db.execute(
            select(User).where(User.id.in_(author_ids))
        )
        for u in authors_result.scalars().all():
            authors_map[u.id] = u

    items = []
    for p in posts:
        author = authors_map.get(p.author_id)
        items.append(_post_to_dict(p, author, liked=p.id in liked_set))

    return {"items": items, "page": page, "size": size}


# ── 点赞/取消 ──

@router.post("/posts/{post_id}/like")
async def toggle_like(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(CommunityPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    # 查是否已点赞
    result = await db.execute(
        select(PostLike).where(
            and_(PostLike.post_id == post_id, PostLike.user_id == current_user.id)
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        await db.delete(existing)
        post.like_count = max(0, post.like_count - 1)
        action = "unliked"
    else:
        like = PostLike(post_id=post_id, user_id=current_user.id)
        db.add(like)
        post.like_count += 1
        action = "liked"

    await db.commit()
    return {"action": action, "like_count": post.like_count}


# ── 发评论 ──

@router.post("/posts/{post_id}/comments", status_code=201)
async def create_comment(
    post_id: int,
    content: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(CommunityPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if not content.strip():
        raise HTTPException(status_code=400, detail="评论内容不能为空")

    comment = PostComment(
        post_id=post_id,
        author_id=current_user.id,
        content=content.strip(),
    )
    db.add(comment)
    post.comment_count += 1
    await db.commit()
    await db.refresh(comment)

    return {
        "id": comment.id,
        "author": {
            "id": current_user.id,
            "nickname": current_user.nickname,
            "avatar_url": current_user.avatar_url,
        },
        "content": comment.content,
        "created_at": comment.created_at.isoformat(),
    }


# ── 获取评论列表 ──

@router.get("/posts/{post_id}/comments")
async def list_comments(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PostComment)
        .where(PostComment.post_id == post_id)
        .order_by(PostComment.created_at.asc())
    )
    comments = result.scalars().all()

    # 加载评论作者
    author_ids = list(set(c.author_id for c in comments))
    authors_map = {}
    if author_ids:
        authors_result = await db.execute(
            select(User).where(User.id.in_(author_ids))
        )
        for u in authors_result.scalars().all():
            authors_map[u.id] = u

    items = []
    for c in comments:
        author = authors_map.get(c.author_id)
        items.append({
            "id": c.id,
            "author": {
                "id": author.id if author else 0,
                "nickname": author.nickname if author else "未知",
                "avatar_url": author.avatar_url if author else None,
            },
            "content": c.content,
            "created_at": c.created_at.isoformat(),
        })

    return items


# ── 删除帖子 ──

@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(CommunityPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能删除自己的帖子")
    await db.delete(post)
    await db.commit()


# ── 通用图片上传接口 ──

@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    try:
        url = await save_upload(file, sub_dir="community")
        return {"url": url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── 工具函数 ──

def _post_to_dict(post: CommunityPost, author, liked: bool) -> dict:
    images = []
    if post.images_json:
        try:
            images = json.loads(post.images_json)
        except json.JSONDecodeError:
            pass

    return {
        "id": post.id,
        "author": {
            "id": author.id if author else 0,
            "nickname": getattr(author, "nickname", None) or "用户",
            "avatar_url": getattr(author, "avatar_url", None),
        },
        "content": post.content,
        "images": images,
        "like_count": post.like_count,
        "comment_count": post.comment_count,
        "liked_by_me": liked,
        "created_at": post.created_at.isoformat(),
    }
