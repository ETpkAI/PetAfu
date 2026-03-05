from __future__ import annotations
import hashlib
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.database import get_db
from app.core.auth import create_access_token, decode_access_token
from app.core.config import get_settings
from app.models.models import User
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/users", tags=["users"])
bearer = HTTPBearer(auto_error=False)
settings = get_settings()

try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")
    USE_BCRYPT = True
except ImportError:
    pwd_context = None
    USE_BCRYPT = False


# ── 密码哈希（bcrypt_sha256 优先，回退 SHA256）──
def _hash_password(password: str) -> str:
    if USE_BCRYPT:
        return pwd_context.hash(password)
    salt = "petafu_salt_2026"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def _verify_password(password: str, hashed: str) -> bool:
    if USE_BCRYPT:
        # bcrypt_sha256 hash 以 $bcrypt-sha256$ 开头，普通 bcrypt 以 $2 开头
        if hashed.startswith("$bcrypt-sha256$") or hashed.startswith("$2"):
            return pwd_context.verify(password, hashed)
        # 回退旧的 SHA256 明文哈希
        salt = "petafu_salt_2026"
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == hashed
    salt = "petafu_salt_2026"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == hashed


# ── 请求/响应模型 ──
class RegisterReq(BaseModel):
    phone: str
    password: str
    nickname: str = ""

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v):
        if not re.fullmatch(r"1[3-9]\d{9}", v):
            raise ValueError("手机号格式不正确")
        return v

    @field_validator("password")
    @classmethod
    def password_length(cls, v):
        if len(v) < 6:
            raise ValueError("密码至少6位")
        return v


class LoginReq(BaseModel):
    phone: str
    password: str


class TokenResp(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    nickname: str
    phone: str


class UserInfo(BaseModel):
    id: int
    phone: str
    nickname: str
    avatar_url: str | None
    created_at: datetime


# ── 依赖：获取当前用户 ──
async def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not cred:
        raise HTTPException(status_code=401, detail="未登录，请先登录")
    sub = decode_access_token(cred.credentials)  # 返回 sub 字符串或 None
    if not sub:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    try:
        # sub 可能是 "{\"sub\": \"1\"}"  或直接 "1"——兼容两种格式
        if isinstance(sub, dict):
            user_id = int(sub.get("sub", 0))
        else:
            user_id = int(sub)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Token 格式错误")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


# ── 注册 ──
@router.post("/register", response_model=TokenResp)
async def register(body: RegisterReq, db: AsyncSession = Depends(get_db)):
    # 查手机号是否已注册
    result = await db.execute(select(User).where(User.phone == body.phone))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="该手机号已注册")

    nickname = body.nickname or f"用户_{body.phone[-4:]}"
    user = User(
        phone=body.phone,
        password_hash=_hash_password(body.password),
        nickname=nickname,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id))
    return TokenResp(
        access_token=token,
        user_id=user.id,
        nickname=user.nickname or "",
        phone=user.phone or "",
    )


# ── 登录 ──
@router.post("/login", response_model=TokenResp)
async def login(body: LoginReq, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == body.phone))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="手机号或密码错误")
    if not _verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="手机号或密码错误")

    token = create_access_token(str(user.id))
    return TokenResp(
        access_token=token,
        user_id=user.id,
        nickname=user.nickname or "",
        phone=user.phone or "",
    )


# ── 获取当前用户信息 ──
@router.get("/me", response_model=UserInfo)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserInfo(
        id=current_user.id,
        phone=current_user.phone or "",
        nickname=current_user.nickname or "",
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at,
    )


# ── 更新昵称 ──
@router.patch("/me")
async def update_me(
    nickname: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.nickname = nickname
    await db.commit()
    return {"message": "更新成功", "nickname": nickname}


# ── 微信登录 ──

class WxLoginReq(BaseModel):
    code: str


@router.post("/wx-login", response_model=TokenResp)
async def wx_login(body: WxLoginReq, db: AsyncSession = Depends(get_db)):
    """微信小程序登录：前端 wx.login() 获取 code，后端换 openid"""
    if not settings.wx_appid or not settings.wx_secret:
        raise HTTPException(status_code=501, detail="微信登录未配置，请设置 WX_APPID 和 WX_SECRET")

    # 调用微信 API 换取 openid
    wx_url = (
        f"https://api.weixin.qq.com/sns/jscode2session"
        f"?appid={settings.wx_appid}&secret={settings.wx_secret}"
        f"&js_code={body.code}&grant_type=authorization_code"
    )
    async with httpx.AsyncClient() as client:
        resp = await client.get(wx_url)
        data = resp.json()

    openid = data.get("openid")
    if not openid:
        errcode = data.get("errcode", "unknown")
        raise HTTPException(status_code=401, detail=f"微信登录失败: {errcode}")

    # 查找或创建用户
    result = await db.execute(select(User).where(User.openid == openid))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            openid=openid,
            nickname=f"微信用户_{openid[-4:]}",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_access_token(str(user.id))
    return TokenResp(
        access_token=token,
        user_id=user.id,
        nickname=user.nickname or "",
        phone=user.phone or "",
    )
