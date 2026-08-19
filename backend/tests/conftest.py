"""Test configuration and fixtures."""

import asyncio
from typing import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.main import app
from app.models.base import Base

settings = get_settings()

# Use a separate test database URL if possible, or same for simplicity in this take-home
# We append _test to avoid wiping the main DB
TEST_DATABASE_URL = settings.database_url + "_test"

engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create tables before tests run and drop them after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Fixture that provides a database session for a test."""
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Fixture that provides an async HTTP client for the FastAPI app."""
    # Override the get_db dependency
    from app.database import get_db
    
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session
            
    app.dependency_overrides[get_db] = override_get_db
    
    # We mock arq pool so tests don't try to connect to Redis for queuing
    class MockArqPool:
        async def enqueue_job(self, *args, **kwargs):
            return None
            
    app.state.arq_pool = MockArqPool()
            
    async with httpx.AsyncClient(app=app, base_url="http://testserver") as test_client:
        yield test_client
        
    app.dependency_overrides.clear()
