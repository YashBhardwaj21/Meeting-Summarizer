"""Chat API routes."""

import uuid

from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.chat import (
    ChatCreate, 
    ChatResponse, 
    AskQuestionRequest, 
    AskQuestionResponse,
    ChatMessageResponse
)
from app.models.chat_message import ChatMessage
from app.services import chat_service
from app.services.rag_service import rag_service
from app.config import get_settings
from sqlalchemy import select

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


@router.post(
    "/{chat_id}/ask",
    response_model=AskQuestionResponse,
    summary="Ask a question about the chat's meetings",
)
async def ask_chat_question_endpoint(
    chat_id: uuid.UUID,
    request: AskQuestionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Query the transcript RAG pipeline."""
    # Ensure chat exists
    await chat_service.get_chat(db, chat_id)
    
    settings = get_settings()
    
    # Load recent conversation history
    history_stmt = (
        select(ChatMessage)
        .where(ChatMessage.chat_id == chat_id)
        .where(ChatMessage.role.in_(["user", "assistant"]))
        .order_by(ChatMessage.created_at.desc())
        .limit(settings.chat_history_turns)
    )
    history_res = await db.execute(history_stmt)
    history_msgs = list(reversed(history_res.scalars().all()))
    history = [{"role": msg.role, "content": msg.content} for msg in history_msgs]
    
    # Save user message
    user_msg = ChatMessage(
        chat_id=chat_id,
        role="user",
        content=request.question
    )
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)
    
    # Get RAG response
    answer, sources = await rag_service.ask_question(db, chat_id, request.question, request.limit, history)
    
    # Save assistant message
    assistant_msg = ChatMessage(
        chat_id=chat_id,
        role="assistant",
        content=answer,
        sources=sources
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)
    
    return AskQuestionResponse(
        message=ChatMessageResponse.model_validate(assistant_msg),
        sources=sources
    )

@router.get(
    "/{chat_id}/messages",
    response_model=list[ChatMessageResponse],
    summary="Get chat messages",
)
async def get_chat_messages_endpoint(
    chat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve conversation history for a chat."""
    # Ensure chat exists
    await chat_service.get_chat(db, chat_id)
    
    stmt = select(ChatMessage).where(ChatMessage.chat_id == chat_id).order_by(ChatMessage.created_at.asc())
    result = await db.execute(stmt)
    return result.scalars().all()
