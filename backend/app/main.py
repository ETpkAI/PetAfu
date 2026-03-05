"""
FastAPI 主应用入口
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db
from app.api import diagnosis, pets, diary, admin, users, medical_records, community, reminders

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动事件：建表 + 加载 RAG 索引"""
    logger.info("🚀 宠物阿福后端启动中...")
    await init_db()
    logger.info("✅ 数据库表已就绪")

    # 异步加载 RAG（非阻塞：首次启动会慢一些）
    from app.services.rag_service import rag_service
    try:
        count = rag_service.build_index()
        logger.info(f"✅ RAG 索引加载完成，新增 {count} 个知识分块")
    except Exception as e:
        logger.warning(f"⚠️ RAG 索引加载失败（可忽略，先跑API）: {e}")

    yield
    logger.info("👋 宠物阿福后端关闭")


app = FastAPI(
    title="宠物阿福 Pet Afu API",
    description="AI宠物健康助手后端，兽医学术文献检索工具",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS（开发阶段放行所有，生产需收紧）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件（图片上传目录）
import os
from fastapi.staticfiles import StaticFiles
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 注册路由
app.include_router(diagnosis.router, prefix="/api/v1")
app.include_router(pets.router, prefix="/api/v1")
app.include_router(diary.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(medical_records.router, prefix="/api/v1")
app.include_router(community.router, prefix="/api/v1")
app.include_router(reminders.router, prefix="/api/v1")
app.include_router(admin.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "宠物阿福 Pet Afu"}
