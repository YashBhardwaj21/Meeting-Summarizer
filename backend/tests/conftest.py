"""Test configuration and fixtures."""

import asyncio
from typing import AsyncGenerator

import httpx
from httpx import ASGITransport
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.main import app
from app.models.base import Base

settings = get_settings()

import asyncio
from sqlalchemy import text

TEST_DATABASE_URL = settings.database_url + "_test"

engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create test DB, create tables before tests run and drop them after."""
    # Connect to the default database to create the test DB
    default_engine = create_async_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    async with default_engine.connect() as conn:
        try:
            await conn.execute(text("CREATE DATABASE meeting_summarizer_test"))
        except Exception as e:
            # Database might already exist
            pass
    await default_engine.dispose()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
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
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
            
    app.dependency_overrides[get_db] = override_get_db
    
    # We mock arq pool so tests don't try to connect to Redis for queuing
    class MockArqPool:
        async def enqueue_job(self, *args, **kwargs):
            return None
            
    app.state.arq_pool = MockArqPool()
            
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
        
    app.dependency_overrides.clear()
