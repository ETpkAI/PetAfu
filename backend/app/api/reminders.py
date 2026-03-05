from __future__ import annotations
"""
提醒服务 API
- 查询即将到期的就诊/疫苗/驱虫提醒
- 后续可对接微信订阅消息推送
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.models.models import MedicalRecord, Pet, User
from app.api.users import get_current_user

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("/upcoming")
async def get_upcoming_reminders(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 N 天内即将到期的提醒（疫苗、驱虫等）"""
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days)

    # 查当前用户所有宠物
    pet_result = await db.execute(
        select(Pet).where(Pet.owner_id == current_user.id)
    )
    pets = pet_result.scalars().all()
    pet_ids = [p.id for p in pets]
    pet_map = {p.id: p for p in pets}

    if not pet_ids:
        return []

    # 查有 next_due_date 的就诊记录
    result = await db.execute(
        select(MedicalRecord).where(
            and_(
                MedicalRecord.pet_id.in_(pet_ids),
                MedicalRecord.next_due_date.isnot(None),
                MedicalRecord.next_due_date <= cutoff,
            )
        ).order_by(MedicalRecord.next_due_date.asc())
    )
    records = result.scalars().all()

    reminders = []
    for r in records:
        pet = pet_map.get(r.pet_id)
        due = r.next_due_date
        days_left = (due - now).days if due else 0
        reminders.append({
            "id": r.id,
            "pet_name": pet.name if pet else "未知",
            "pet_id": r.pet_id,
            "record_type": r.record_type,
            "title": r.title,
            "next_due_date": due.isoformat() if due else None,
            "days_left": days_left,
            "is_overdue": days_left < 0,
            "urgency": "overdue" if days_left < 0 else
                       "urgent" if days_left <= 7 else
                       "upcoming",
        })

    return reminders


@router.get("/today-digest")
async def today_digest(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """今日概要：过期 + 7天内到期的提醒数"""
    now = datetime.now(timezone.utc)
    seven_days = now + timedelta(days=7)

    pet_result = await db.execute(
        select(Pet.id).where(Pet.owner_id == current_user.id)
    )
    pet_ids = [pid for pid in pet_result.scalars().all()]

    if not pet_ids:
        return {"overdue": 0, "upcoming_7d": 0, "total": 0}

    # 过期
    overdue_result = await db.execute(
        select(MedicalRecord).where(
            and_(
                MedicalRecord.pet_id.in_(pet_ids),
                MedicalRecord.next_due_date.isnot(None),
                MedicalRecord.next_due_date < now,
            )
        )
    )
    overdue = len(overdue_result.scalars().all())

    # 7天内
    upcoming_result = await db.execute(
        select(MedicalRecord).where(
            and_(
                MedicalRecord.pet_id.in_(pet_ids),
                MedicalRecord.next_due_date.isnot(None),
                MedicalRecord.next_due_date >= now,
                MedicalRecord.next_due_date <= seven_days,
            )
        )
    )
    upcoming = len(upcoming_result.scalars().all())

    return {
        "overdue": overdue,
        "upcoming_7d": upcoming,
        "total": overdue + upcoming,
    }
