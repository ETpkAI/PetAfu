from __future__ import annotations
"""
图片上传服务
- MVP 阶段使用本地磁盘存储
- 通过 FastAPI StaticFiles 提供访问
- 后续可切换为腾讯云 COS / 阿里云 OSS
"""
import os
import uuid
import logging
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 上传目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


async def save_upload(file: UploadFile, sub_dir: str = "images") -> str:
    """
    保存上传文件，返回相对 URL 路径。
    sub_dir: 子目录，如 "images", "avatars"
    """
    if file.content_type not in ALLOWED_TYPES:
        raise ValueError(f"不支持的文件类型: {file.content_type}，仅支持 JPEG/PNG/WebP/GIF")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise ValueError("文件大小不能超过 10MB")

    # 生成唯一文件名
    ext = file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"

    target_dir = UPLOAD_DIR / sub_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    filepath = target_dir / filename
    with open(filepath, "wb") as f:
        f.write(content)

    # 返回相对 URL
    url = f"/uploads/{sub_dir}/{filename}"
    logger.info(f"文件已保存: {url} ({len(content)} bytes)")
    return url
