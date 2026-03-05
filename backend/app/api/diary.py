from __future__ import annotations
from typing import Optional
"""
健康日记 API
- 记录每日精神/食欲/排便状态
- 连续3天食欲不振触发预警
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.models.models import HealthDiary

router = APIRouter(prefix="/diary", tags=["diary"])


class DiaryCreate(BaseModel):
    user_id: int
    pet_id: int
    appetite_score: Optional[int] = None   # 1-5
    energy_score: Optional[int] = None     # 1-5
    stool_normal: Optional[bool] = None
    notes: Optional[str] = None


class DiaryOut(BaseModel):
    id: int
    pet_id: int
    appetite_score: Optional[int]
    energy_score: Optional[int]
    stool_normal: Optional[bool]
    notes: Optional[str]
    recorded_at: datetime

    model_config = {"from_attributes": True}


@router.post("/", response_model=DiaryOut, status_code=201)
async def create_diary(payload: DiaryCreate, db: AsyncSession = Depends(get_db)):
    diary = HealthDiary(**payload.model_dump())
    db.add(diary)
    await db.commit()
    await db.refresh(diary)

    # 检查连续3天食欲不振
    alert = await _check_appetite_alert(payload.pet_id, db)

    return {**DiaryOut.model_validate(diary).model_dump(), "_alert": alert}


async def _check_appetite_alert(pet_id: int, db: AsyncSession) -> Optional[str]:
    """若过去3天 appetite_score <= 2，返回预警文字"""
    three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
    result = await db.execute(
        select(HealthDiary)
        .where(
            and_(
                HealthDiary.pet_id == pet_id,
                HealthDiary.recorded_at >= three_days_ago,
                HealthDiary.appetite_score <= 2,
            )
        )
    )
    records = result.scalars().all()
    if len(records) >= 3:
        return "⚠️ 您的宠物已连续3天以上食欲不振，建议尽快前往宠物医院检查！"
    return None


@router.get("/{pet_id}", response_model=list[DiaryOut])
async def list_diary(pet_id: int, limit: int = 30, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(HealthDiary)
        .where(HealthDiary.pet_id == pet_id)
        .order_by(HealthDiary.recorded_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
