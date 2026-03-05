import ssl
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

_db_url = settings.database_url

# 判断是否使用 SQLite（本地开发 / 测试）
_is_sqlite = _db_url.startswith("sqlite")

if _is_sqlite:
    # SQLite 不需要 SSL，也不需要连接池
    engine = create_async_engine(
        _db_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL (Supabase) 需要 SSL
    _ssl_ctx = ssl.create_default_context()
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = ssl.CERT_NONE

    _db_url = _db_url.replace("?ssl=require", "")

    engine = create_async_engine(
        _db_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=60,
        connect_args={"ssl": _ssl_ctx},
    )

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    """FastAPI 依赖注入：获取数据库 session"""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """启动时自动建表（开发阶段用，生产请用 Alembic）"""
    from app.models.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
