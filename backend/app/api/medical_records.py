from __future__ import annotations
from typing import Optional
"""
就诊/疫苗/驱虫记录 CRUD API
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.models import MedicalRecord, Pet
from app.api.users import get_current_user, User

router = APIRouter(prefix="/medical-records", tags=["medical_records"])


class MedicalRecordCreate(BaseModel):
    pet_id: int
    record_type: str       # "vaccine" | "deworming" | "visit" | "surgery" | "other"
    title: str
    description: Optional[str] = None
    next_due_date: Optional[str] = None   # ISO 格式 "2026-06-15"
    occurred_at: str                       # ISO 格式 "2026-03-04"


class MedicalRecordOut(BaseModel):
    id: int
    pet_id: int
    record_type: str
    title: str
    description: Optional[str]
    next_due_date: Optional[datetime]
    occurred_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class MedicalRecordUpdate(BaseModel):
    record_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    next_due_date: Optional[str] = None
    occurred_at: Optional[str] = None


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


@router.post("/", response_model=MedicalRecordOut, status_code=201)
async def create_record(
    payload: MedicalRecordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 验证宠物归属
    pet = await db.get(Pet, payload.pet_id)
    if not pet or pet.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="宠物档案不存在")

    occurred = _parse_dt(payload.occurred_at)
    if not occurred:
        raise HTTPException(status_code=400, detail="occurred_at 格式错误，请用 ISO 格式")

    record = MedicalRecord(
        pet_id=payload.pet_id,
        record_type=payload.record_type,
        title=payload.title,
        description=payload.description,
        next_due_date=_parse_dt(payload.next_due_date),
        occurred_at=occurred,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/{pet_id}", response_model=list[MedicalRecordOut])
async def list_records(
    pet_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 验证宠物归属
    pet = await db.get(Pet, pet_id)
    if not pet or pet.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="宠物档案不存在")

    result = await db.execute(
        select(MedicalRecord)
        .where(MedicalRecord.pet_id == pet_id)
        .order_by(MedicalRecord.occurred_at.desc())
    )
    return result.scalars().all()


@router.patch("/{record_id}", response_model=MedicalRecordOut)
async def update_record(
    record_id: int,
    payload: MedicalRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(MedicalRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 验证宠物归属
    pet = await db.get(Pet, record.pet_id)
    if not pet or pet.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无操作权限")

    if payload.record_type is not None:
        record.record_type = payload.record_type
    if payload.title is not None:
        record.title = payload.title
    if payload.description is not None:
        record.description = payload.description
    if payload.next_due_date is not None:
        record.next_due_date = _parse_dt(payload.next_due_date)
    if payload.occurred_at is not None:
        parsed = _parse_dt(payload.occurred_at)
        if parsed:
            record.occurred_at = parsed

    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=204)
async def delete_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(MedicalRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    pet = await db.get(Pet, record.pet_id)
    if not pet or pet.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无操作权限")

    await db.delete(record)
    await db.commit()
