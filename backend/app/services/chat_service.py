"""Chat service — handles business logic for chat workspaces."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from arq.connections import ArqRedis

from app.models.chat import Chat
from app.models.enums import ChatStatus
from app.utils.exceptions import NotFoundError


async def create_chat(db: AsyncSession, title: str | None = None) -> Chat:
    """Create a new chat workspace.

    Args:
        db: Async database session
        title: Optional title for the chat

    Returns:
        The newly created Chat record.
    """
    chat = Chat(title=title)
    db.add(chat)
    await db.flush()
    return chat


async def list_chats(db: AsyncSession) -> list[Chat]:
    """Retrieve all active chat workspaces.
    
    Args:
        db: Async database session
        
    Returns:
        List of active Chat records ordered by newest first.
    """
    stmt = select(Chat).where(
        Chat.status == ChatStatus.ACTIVE.value,
        Chat.deleted_at.is_(None)
    ).order_by(Chat.created_at.desc())
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_chat(db: AsyncSession, chat_id: uuid.UUID) -> Chat:
    """Retrieve an active chat workspace by ID.

    Args:
        db: Async database session
        chat_id: The UUID of the chat

    Returns:
        The Chat record.

    Raises:
        NotFoundError: If chat does not exist or is deleted/deleting.
    """
    stmt = select(Chat).where(
        Chat.id == chat_id,
        Chat.status == ChatStatus.ACTIVE.value,
    )
    result = await db.execute(stmt)
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise NotFoundError("Chat not found or is no longer active.")
        
    return chat


async def delete_chat(db: AsyncSession, arq_pool: ArqRedis, chat_id: uuid.UUID) -> None:
    """Mark a chat as deleting.
    
    The actual cascading cleanup (files in storage, database records) 
    happens asynchronously via a background worker (implemented in Step 8/9).

    Args:
        db: Async database session
        chat_id: The UUID of the chat

    Raises:
        NotFoundError: If chat does not exist or is already deleted/deleting.
    """
    chat = await get_chat(db, chat_id)
    
    # Mark as deleting. Real deletion is asynchronous.
    chat.status = ChatStatus.DELETING.value
    await db.flush()
    
    # Enqueue cleanup worker job using arq
    await arq_pool.enqueue_job(
        "cleanup_chat",
        chat_id_hex=chat_id.hex,
    )
