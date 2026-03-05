from __future__ import annotations
from typing import Optional
"""
宠物档案 CRUD API（已接入 JWT 鉴权）
"""
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.models import Pet, PetSpecies, PetGender
from app.api.users import get_current_user, User

router = APIRouter(prefix="/pets", tags=["pets"])


class PetCreate(BaseModel):
    name: str
    species: PetSpecies = PetSpecies.cat
    breed: Optional[str] = None
    gender: PetGender = PetGender.unknown
    birth_date: Optional[str] = None   # ISO 格式 "2022-03-15"
    weight_kg: Optional[float] = None
    is_neutered: bool = False


class PetOut(BaseModel):
    id: int
    name: str
    species: PetSpecies
    breed: Optional[str]
    gender: PetGender
    birth_date: Optional[datetime]
    weight_kg: Optional[float]
    is_neutered: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PetUpdate(BaseModel):
    name: Optional[str] = None
    species: Optional[PetSpecies] = None
    breed: Optional[str] = None
    gender: Optional[PetGender] = None
    birth_date: Optional[str] = None
    weight_kg: Optional[float] = None
    is_neutered: Optional[bool] = None


@router.post("/", response_model=PetOut, status_code=201)
async def create_pet(
    payload: PetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    birth_dt = None
    if payload.birth_date:
        try:
            birth_dt = datetime.strptime(payload.birth_date, "%Y-%m-%d")
        except ValueError:
            pass

    pet = Pet(
        owner_id=current_user.id,
        name=payload.name,
        species=payload.species,
        breed=payload.breed,
        gender=payload.gender,
        birth_date=birth_dt,
        weight_kg=payload.weight_kg,
        is_neutered=payload.is_neutered,
    )
    db.add(pet)
    await db.commit()
    await db.refresh(pet)
    return pet


@router.get("/mine", response_model=list[PetOut])
async def list_my_pets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Pet).where(Pet.owner_id == current_user.id))
    return result.scalars().all()


@router.get("/{owner_id}", response_model=list[PetOut])
async def list_pets(owner_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Pet).where(Pet.owner_id == owner_id))
    return result.scalars().all()


@router.patch("/{pet_id}/weight")
async def update_weight(
    pet_id: int,
    weight_kg: float,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pet = await db.get(Pet, pet_id)
    if not pet or pet.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="宠物档案不存在")
    pet.weight_kg = weight_kg
    await db.commit()
    return {"message": "体重已更新", "weight_kg": weight_kg}


@router.patch("/{pet_id}", response_model=PetOut)
async def update_pet(
    pet_id: int,
    payload: PetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pet = await db.get(Pet, pet_id)
    if not pet or pet.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="宠物档案不存在")

    if payload.name is not None:
        pet.name = payload.name
    if payload.species is not None:
        pet.species = payload.species
    if payload.breed is not None:
        pet.breed = payload.breed
    if payload.gender is not None:
        pet.gender = payload.gender
    if payload.birth_date is not None:
        try:
            pet.birth_date = datetime.strptime(payload.birth_date, "%Y-%m-%d") if payload.birth_date else None
        except ValueError:
            pass
    if payload.weight_kg is not None:
        pet.weight_kg = payload.weight_kg
    if payload.is_neutered is not None:
        pet.is_neutered = payload.is_neutered

    await db.commit()
    await db.refresh(pet)
    return pet


@router.delete("/{pet_id}", status_code=204)
async def delete_pet(
    pet_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pet = await db.get(Pet, pet_id)
    if not pet or pet.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="宠物档案不存在")
    await db.delete(pet)
    await db.commit()
