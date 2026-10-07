import asyncio
import os
import sys
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_applymate.db"

for module_name in list(sys.modules):
    if module_name.startswith("app.core.config") or module_name.startswith("app.database.database") or module_name.startswith("app.main"):
        sys.modules.pop(module_name)

import app.core.config as app_config
app_config.get_settings.cache_clear()
app_config.settings = app_config.get_settings()
app_config.settings.database_url = os.environ["DATABASE_URL"]

import app.database.database as database_module

database_module.engine = create_async_engine(os.environ["DATABASE_URL"], future=True, echo=False)
database_module.AsyncSessionLocal = async_sessionmaker(
    bind=database_module.engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

from app.main import app
from app.database.database import AsyncSessionLocal, Base, engine
from app.models.user import User
from app.core.security import create_access_token, hash_password


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        async with AsyncSessionLocal(bind=connection) as session:
            yield session
        await connection.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def authenticated_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password=hash_password("secret123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(user.id)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[database_module.get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            client.headers.update({"Authorization": f"Bearer {token}"})
            yield client
    finally:
        app.dependency_overrides.clear()
