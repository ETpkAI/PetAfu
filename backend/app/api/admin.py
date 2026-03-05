"""
管理员 API
- POST /admin/login   → 返回 JWT token
- GET  /admin/stats   → 总用户数、宠物数、日记数（需要 token）
- GET  /admin/        → 管理员面板 HTML 页面
"""
from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import get_settings
from app.core.auth import create_access_token, decode_access_token
from app.core.database import get_db
from app.models.models import User, Pet, HealthDiary, CommunityPost, MedicalRecord, PostComment

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()
bearer = HTTPBearer(auto_error=False)


def _require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials:
        raise HTTPException(status_code=401, detail="未提供 Token")
    sub = decode_access_token(credentials.credentials)
    if sub != "admin":
        raise HTTPException(status_code=403, detail="无效的管理员 Token")
    return sub


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=LoginResponse)
async def admin_login(body: LoginRequest):
    if body.username != settings.admin_username or body.password != settings.admin_password:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token("admin")
    return {"access_token": token, "token_type": "bearer"}


@router.get("/stats")
async def admin_stats(_: str = Depends(_require_admin), db: AsyncSession = Depends(get_db)):
    user_count = (await db.execute(select(func.count()).select_from(User))).scalar()
    pet_count = (await db.execute(select(func.count()).select_from(Pet))).scalar()
    diary_count = (await db.execute(select(func.count()).select_from(HealthDiary))).scalar()
    post_count = (await db.execute(select(func.count()).select_from(CommunityPost))).scalar()
    record_count = (await db.execute(select(func.count()).select_from(MedicalRecord))).scalar()
    comment_count = (await db.execute(select(func.count()).select_from(PostComment))).scalar()
    return {
        "users": user_count,
        "pets": pet_count,
        "diaries": diary_count,
        "posts": post_count,
        "records": record_count,
        "comments": comment_count,
        "server_time": datetime.now().isoformat(),
    }


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def admin_page():
    """返回管理员面板 SPA"""
    with open("app/admin_panel.html", encoding="utf-8") as f:
        return f.read()
