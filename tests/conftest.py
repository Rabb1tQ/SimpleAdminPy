"""
测试配置和工具函数
"""
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.redis import get_redis, get_redis_cache
from app.core.security import get_password_hash, create_access_token
from app.models import User, Role, Menu, DictType, DictData, LoginLog, OperationLog, Tenant
from app.models.system.role import user_role, role_menu
from app.api import api_router


# 测试数据库 URL (使用 SQLite 内存数据库)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_engine():
    """创建测试数据库引擎 - 每个测试独立数据库"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def app() -> FastAPI:
    """创建测试应用"""
    test_app = FastAPI()
    test_app.include_router(api_router, prefix="/api")
    return test_app


# Mock Redis 客户端 - 必须在 client fixture 之前定义
@pytest.fixture
def mock_redis():
    """Mock Redis 客户端"""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.exists = AsyncMock(return_value=0)
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.smembers = AsyncMock(return_value=[])
    redis_mock.sadd = AsyncMock(return_value=1)
    redis_mock.srem = AsyncMock(return_value=1)
    return redis_mock


@pytest_asyncio.fixture
async def client(app: FastAPI, db_session: AsyncSession, mock_redis: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端"""
    
    async def override_get_db():
        yield db_session
    
    async def override_get_redis():
        yield mock_redis
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    app.dependency_overrides[get_redis_cache] = override_get_redis
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """创建测试用户"""
    user = User(
        username="testuser",
        password=get_password_hash("testpass123"),
        real_name="测试用户",
        email="test@example.com",
        phone="13800138000",
        status=1,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_superuser(db_session: AsyncSession) -> User:
    """创建测试超级管理员"""
    user = User(
        username="admin",
        password=get_password_hash("admin123"),
        real_name="超级管理员",
        email="admin@example.com",
        phone="13800138001",
        status=1,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_role(db_session: AsyncSession) -> Role:
    """创建测试角色"""
    role = Role(
        name="测试角色",
        code="test_role",
        desc="用于测试的角色",
        status=1,
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


@pytest_asyncio.fixture
async def test_menu(db_session: AsyncSession) -> Menu:
    """创建测试菜单"""
    menu = Menu(
        name="测试菜单",
        path="/test",
        component="test/index",
        title="测试菜单",
        icon="test-icon",
        sort=1,
        status=1,
    )
    db_session.add(menu)
    await db_session.commit()
    await db_session.refresh(menu)
    return menu


@pytest_asyncio.fixture
async def test_dict(db_session: AsyncSession) -> DictType:
    """创建测试字典类型"""
    dict_obj = DictType(
        name="测试字典",
        code="test_dict",
        status=1,
    )
    db_session.add(dict_obj)
    await db_session.commit()
    await db_session.refresh(dict_obj)
    return dict_obj


@pytest_asyncio.fixture
async def test_dict_item(db_session: AsyncSession, test_dict: DictType) -> DictData:
    """创建测试字典数据"""
    item = DictData(
        dict_type_id=test_dict.id,
        label="测试项",
        value="test_value",
        sort=1,
        status=1,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """生成认证请求头"""
    token = create_access_token(str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def superuser_auth_headers(test_superuser: User) -> dict:
    """生成超级管理员认证请求头"""
    token = create_access_token(str(test_superuser.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def user_with_role(db_session: AsyncSession, test_user: User, test_role: Role) -> User:
    """创建带角色的用户"""
    # 直接插入关联表，避免懒加载问题
    from sqlalchemy import insert
    await db_session.execute(
        insert(user_role).values(user_id=test_user.id, role_id=test_role.id)
    )
    await db_session.commit()
    await db_session.refresh(test_user)
    return test_user


@pytest_asyncio.fixture
async def role_with_menu(db_session: AsyncSession, test_role: Role, test_menu: Menu) -> Role:
    """创建带菜单权限的角色"""
    # 直接插入关联表，避免懒加载问题
    from sqlalchemy import insert
    await db_session.execute(
        insert(role_menu).values(role_id=test_role.id, menu_id=test_menu.id)
    )
    await db_session.commit()
    await db_session.refresh(test_role)
    return test_role


# Mock Redis 依赖
@pytest.fixture
def mock_redis_deps(mock_redis):
    """Mock Redis 依赖注入"""
    with patch("app.api.auth.get_redis", return_value=mock_redis):
        with patch("app.core.redis.RedisClient.get_session_client", return_value=mock_redis):
            yield mock_redis


@pytest_asyncio.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """创建测试租户"""
    tenant = Tenant(
        name="测试租户",
        code="test_tenant",
        contact="测试联系人",
        phone="13800138002",
        email="tenant@example.com",
        status=1,
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def test_tenant2(db_session: AsyncSession) -> Tenant:
    """创建第二个测试租户"""
    tenant = Tenant(
        name="测试租户2",
        code="test_tenant2",
        contact="测试联系人2",
        phone="13800138003",
        email="tenant2@example.com",
        status=1,
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def tenant_admin(db_session: AsyncSession, test_tenant: Tenant, test_role: Role) -> User:
    """创建租户管理员用户"""
    from sqlalchemy import insert
    user = User(
        username="tenant_admin",
        password=get_password_hash("admin123"),
        real_name="租户管理员",
        email="tenant_admin@example.com",
        phone="13800138004",
        status=1,
        is_superuser=False,
        tenant_id=test_tenant.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # 分配租户管理员角色
    await db_session.execute(
        insert(user_role).values(user_id=user.id, role_id=test_role.id)
    )
    await db_session.commit()
    return user
