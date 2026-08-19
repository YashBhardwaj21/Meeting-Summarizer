"""API v1 router — aggregates all sub-routers."""

from fastapi import APIRouter

api_v1_router = APIRouter()

# Sub-routers will be included here as they are implemented:
from app.api.v1.chats import router as chats_router
from app.api.v1.files import router as files_router
from app.api.v1.meetings import router as meetings_router
from app.api.v1.jobs import router as jobs_router

api_v1_router.include_router(chats_router)
api_v1_router.include_router(files_router)
api_v1_router.include_router(meetings_router)
api_v1_router.include_router(jobs_router)
