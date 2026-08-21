"""Chat API routes."""

import uuid

from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.chat import ChatCreate, ChatResponse
from app.services import chat_service

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get(
    "",
    response_model=list[ChatResponse],
    summary="List active chats",
)
async def list_chats_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """Retrieves all active chat workspaces."""
    return await chat_service.list_chats(db)


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat",
)
async def create_chat_endpoint(
    request: ChatCreate,
    db: AsyncSession = Depends(get_db),
):
    """Creates a new chat workspace. Returns the newly generated chat ID."""
    return await chat_service.create_chat(db, title=request.title)


@router.get(
    "/{chat_id}",
    response_model=ChatResponse,
    summary="Get chat details",
)
async def get_chat_endpoint(
    chat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for an active chat."""
    return await chat_service.get_chat(db, chat_id)


@router.delete(
    "/{chat_id}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Delete a chat",
)
async def delete_chat_endpoint(
    chat_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Mark a chat for deletion. 
    
    This initiates an asynchronous cascading cleanup of all associated files, 
    meetings, and objects in storage. Returns 202 Accepted.
    """
    arq_pool = request.app.state.arq_pool
    await chat_service.delete_chat(db, arq_pool, chat_id)
    return {"status": "accepted"}
