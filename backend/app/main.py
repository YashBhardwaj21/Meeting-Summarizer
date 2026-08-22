"""FastAPI application factory and lifespan."""

from __future__ import annotations

from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.v1.router import api_v1_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hooks."""
    # ── Startup ──────────────────────────────────────────────────
    app.state.redis = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    
    # Initialize arq Redis pool for job queuing
    import arq
    app.state.arq_pool = await arq.create_pool(
        arq.connections.RedisSettings.from_dsn(settings.redis_url)
    )
    
    # Ensure storage bucket exists (MinIO/R2)
    from app.services.storage_service import ensure_bucket_exists
    ensure_bucket_exists()
    
    yield
    # ── Shutdown ─────────────────────────────────────────────────
    if hasattr(app.state, "arq_pool"):
        await app.state.arq_pool.close()
    await app.state.redis.close()


app = FastAPI(
    title=settings.app_name,
    description="Evidence-grounded meeting assistant with persistent chat-scoped context.",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Middleware & Exception Handlers ──────────────────────────────────
from app.api.middleware import setup_middleware
setup_middleware(app)

# ── API routers ──────────────────────────────────────────────────────
app.include_router(api_v1_router, prefix="/api/v1")


# ── Health endpoints ─────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health():
    """Basic liveness check — is the process running?"""
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
async def ready():
    """Readiness check — can the app serve traffic?

    Verifies connectivity to PostgreSQL and Redis.
    """
    checks: dict[str, str] = {}

    # Check Redis
    try:
        redis_client: aioredis.Redis = app.state.redis
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    # Check PostgreSQL
    try:
        from app.database import engine

        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"

    # Check MinIO
    try:
        from app.services.storage_service import get_boto3_client, settings as storage_settings
        s3 = get_boto3_client()
        s3.head_bucket(Bucket=storage_settings.s3_bucket_name)
        checks["minio"] = "ok"
    except Exception as exc:
        checks["minio"] = f"error: {exc}"

    # Check ARQ
    try:
        if hasattr(app.state, "arq_pool"):
            await app.state.arq_pool.ping()
            checks["arq"] = "ok"
        else:
            checks["arq"] = "error: arq_pool not initialized"
    except Exception as exc:
        checks["arq"] = f"error: {exc}"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
    }
