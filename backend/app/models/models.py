from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Integer, Float, DateTime, Text, ForeignKey, Enum, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    pass


class PetSpecies(str, enum.Enum):
    cat = "cat"
    dog = "dog"
    other = "other"


class PetGender(str, enum.Enum):
    male = "male"
    female = "female"
    unknown = "unknown"


class User(Base):
    """用户表（支持手机号注册 + 微信登录）"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # 微信登录
    openid: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True, nullable=True)
    # 手机号注册登录
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    pets: Mapped[List["Pet"]] = relationship(back_populates="owner")
    health_diaries: Mapped[List["HealthDiary"]] = relationship(back_populates="user")
    community_posts: Mapped[List["CommunityPost"]] = relationship(back_populates="author")


class Pet(Base):
    """宠物档案表"""
    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(32))
    species: Mapped[PetSpecies] = mapped_column(Enum(PetSpecies), default=PetSpecies.cat)
    breed: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    gender: Mapped[PetGender] = mapped_column(Enum(PetGender), default=PetGender.unknown)
    birth_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_neutered: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    owner: Mapped["User"] = relationship(back_populates="pets")
    health_diaries: Mapped[List["HealthDiary"]] = relationship(back_populates="pet")
    medical_records: Mapped[List["MedicalRecord"]] = relationship(back_populates="pet")


class HealthDiary(Base):
    """宠物每日健康日记"""
    __tablename__ = "health_diaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"), index=True)
    appetite_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    energy_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stool_normal: Mapped[Optional[bool]] = mapped_column(nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="health_diaries")
    pet: Mapped["Pet"] = relationship(back_populates="health_diaries")


class MedicalRecord(Base):
    """就诊/疫苗/驱虫记录"""
    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"), index=True)
    record_type: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    pet: Mapped["Pet"] = relationship(back_populates="medical_records")


# ── 社区模型 ──────────────────────────────────────────────────────

class CommunityPost(Base):
    """宠友圈帖子"""
    __tablename__ = "community_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    # 以 JSON 字符串存储图片 URL 列表，如 '["url1","url2"]'
    images_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    author: Mapped["User"] = relationship(back_populates="community_posts")
    likes: Mapped[List["PostLike"]] = relationship(back_populates="post", cascade="all, delete-orphan")
    comments: Mapped[List["PostComment"]] = relationship(back_populates="post", cascade="all, delete-orphan")


class PostLike(Base):
    """帖子点赞"""
    __tablename__ = "post_likes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("community_posts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    post: Mapped["CommunityPost"] = relationship(back_populates="likes")


class PostComment(Base):
    """帖子评论"""
    __tablename__ = "post_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("community_posts.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    post: Mapped["CommunityPost"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship()
