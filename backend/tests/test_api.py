"""
宠物阿福后端基础测试
- 使用 SQLite 内存数据库，不依赖远程 Supabase
- 每次测试 session 独立创建数据库
"""
import os
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport

# 强制使用 SQLite 内存数据库（在 import app 之前设置）
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///file:test?mode=memory&cache=shared&uri=true"

from app.main import app
from app.core.database import engine, Base


@pytest.fixture(scope="session")
def event_loop():
    """全局共享一个 event loop，避免 loop closed 错误。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    """在测试开始前创建所有表，测试结束后清理。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


transport = ASGITransport(app=app)


async def _client():
    return AsyncClient(transport=transport, base_url="http://test")


# ── 健康检查 ──

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


# ── 用户注册 ──

@pytest.mark.asyncio
async def test_register():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/users/register", json={
            "phone": "13800138000",
            "password": "test123456",
            "nickname": "测试用户",
        })
        assert resp.status_code in (200, 409)
        if resp.status_code == 200:
            data = resp.json()
            assert "access_token" in data
            assert data["nickname"] == "测试用户"


# ── 用户登录 ──

@pytest.mark.asyncio
async def test_login():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 先注册（可能已存在）
        await client.post("/api/v1/users/register", json={
            "phone": "13800138001",
            "password": "test123456",
        })
        # 登录
        resp = await client.post("/api/v1/users/login", json={
            "phone": "13800138001",
            "password": "test123456",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/users/login", json={
            "phone": "13800138001",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401


# ── 用户信息 ──

@pytest.mark.asyncio
async def test_get_me():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/v1/users/register", json={
            "phone": "13800138002",
            "password": "test123456",
            "nickname": "信息测试",
        })
        if reg.status_code == 409:
            login = await client.post("/api/v1/users/login", json={
                "phone": "13800138002",
                "password": "test123456",
            })
            token = login.json()["access_token"]
        else:
            token = reg.json()["access_token"]

        resp = await client.get("/api/v1/users/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["phone"] == "13800138002"


# ── 宠物 CRUD ──

@pytest.mark.asyncio
async def test_pet_crud():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/v1/users/register", json={
            "phone": "13800138003",
            "password": "test123456",
        })
        if reg.status_code == 409:
            login = await client.post("/api/v1/users/login", json={
                "phone": "13800138003",
                "password": "test123456",
            })
            token = login.json()["access_token"]
        else:
            token = reg.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # 创建宠物
        create_resp = await client.post("/api/v1/pets/", json={
            "name": "小虎",
            "species": "cat",
            "breed": "英短",
        }, headers=headers)
        assert create_resp.status_code in (200, 201)
        pet = create_resp.json()
        pet_id = pet["id"]

        # 列表
        list_resp = await client.get("/api/v1/pets/mine", headers=headers)
        assert list_resp.status_code == 200
        assert any(p["id"] == pet_id for p in list_resp.json())

        # 更新
        update_resp = await client.patch(f"/api/v1/pets/{pet_id}", json={
            "name": "大虎",
            "weight_kg": 5.5,
        }, headers=headers)
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "大虎"

        # 删除
        delete_resp = await client.delete(f"/api/v1/pets/{pet_id}", headers=headers)
        assert delete_resp.status_code == 200


# ── 管理员登录 ──

@pytest.mark.asyncio
async def test_admin_login():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/admin/login", json={
            "username": "admin",
            "password": "PetAfu@2026!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data


@pytest.mark.asyncio
async def test_admin_stats():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_resp = await client.post("/admin/login", json={
            "username": "admin",
            "password": "PetAfu@2026!",
        })
        token = login_resp.json()["access_token"]

        resp = await client.get("/admin/stats", headers={
            "Authorization": f"Bearer {token}"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert "pets" in data
        assert "posts" in data


# ── 未授权访问 ──

@pytest.mark.asyncio
async def test_unauthorized():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/pets/mine")
        assert resp.status_code in (401, 403)

        resp = await client.get("/api/v1/users/me")
        assert resp.status_code in (401, 403)
