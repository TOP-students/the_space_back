import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, or_, asc
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from models import User, Chat, ChatParticipant, Message
from schemas import (
    PrivateChatCreate,
    ChatResponse,
    MessageCreate,
    MessageOut
)
from utils import get_async_db, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chats", tags=["chats"])
limiter = Limiter(key_func=get_remote_address)


@router.post("", response_model=ChatResponse)
async def create_private_chat(
    chat_data: PrivateChatCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a private chat between two users."""
    try:
        if chat_data.user2_id == current_user.id:
            raise HTTPException(
                status_code=400,
                detail="Нельзя создать чат с самим собой"
            )

        # Check if user2 exists
        result = await db.execute(
            select(User).filter(User.id == chat_data.user2_id)
        )
        user2 = result.scalar_one_or_none()
        if not user2:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Check if chat already exists
        query = select(Chat).filter(
            or_(
                (Chat.user1_id == current_user.id) &
                (Chat.user2_id == chat_data.user2_id),
                (Chat.user1_id == chat_data.user2_id) &
                (Chat.user2_id == current_user.id)
            )
        )
        result = await db.execute(query)
        existing_chat = result.scalar_one_or_none()

        if existing_chat:
            raise HTTPException(status_code=400, detail="Чат уже существует")

        # Create new chat
        new_chat = Chat(
            type="private",
            user1_id=current_user.id,
            user2_id=chat_data.user2_id
        )
        db.add(new_chat)
        await db.flush()

        # Add participants
        participant1 = ChatParticipant(
            chat_id=new_chat.id,
            user_id=current_user.id,
            is_active=True
        )
        participant2 = ChatParticipant(
            chat_id=new_chat.id,
            user_id=chat_data.user2_id,
            is_active=True
        )
        db.add_all([participant1, participant2])
        await db.commit()
        await db.refresh(new_chat)

        logger.info(f"Private chat created: {new_chat.id}")
        return ChatResponse(chat_id=new_chat.id, message="Private чат создан")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating chat: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Ошибка при создании чата"
        )


@router.get("/{chat_id}/messages", response_model=List[MessageOut])
async def get_messages(
    chat_id: int,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get messages from a chat."""
    try:
        # Check if chat exists
        result = await db.execute(select(Chat).filter(Chat.id == chat_id))
        chat = result.scalar_one_or_none()
        if not chat:
            raise HTTPException(status_code=404, detail="Чат не найден")

        # Check if user is participant
        result = await db.execute(
            select(ChatParticipant).filter(
                ChatParticipant.chat_id == chat_id,
                ChatParticipant.user_id == current_user.id,
                ChatParticipant.is_active.is_(True)
            )
        )
        participant = result.scalar_one_or_none()
        if not participant:
            raise HTTPException(
                status_code=403,
                detail="Вы не участник чата"
            )

        # Get messages
        query = (
            select(Message)
            .filter(Message.chat_id == chat_id, Message.is_deleted.is_(False))
            .order_by(asc(Message.created_at))
            .limit(limit)
        )
        result = await db.execute(query)
        messages = result.scalars().all()

        return messages

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(
            status_code=500,
            detail="Ошибка при получении сообщений"
        )


@router.post("/{chat_id}/messages", response_model=MessageOut)
@limiter.limit("10/minute")
async def send_message(
    chat_id: int,
    message: MessageCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Send a message in a chat."""
    try:
        # Check if chat exists
        result = await db.execute(select(Chat).filter(Chat.id == chat_id))
        chat = result.scalar_one_or_none()
        if not chat:
            raise HTTPException(status_code=404, detail="Чат не найден")

        # Check if user is active participant
        result = await db.execute(
            select(ChatParticipant).filter(
                ChatParticipant.chat_id == chat_id,
                ChatParticipant.user_id == current_user.id,
                ChatParticipant.is_active.is_(True)
            )
        )
        participant = result.scalar_one_or_none()
        if not participant:
            raise HTTPException(
                status_code=403,
                detail="Вы не участник чата"
            )

        # Create message
        new_message = Message(
            chat_id=chat_id,
            user_id=current_user.id,
            content=message.content,
            type=message.type,
            attachment_id=message.attachment_id
        )
        db.add(new_message)
        await db.commit()
        await db.refresh(new_message)

        logger.info(f"Message sent in chat {chat_id}")

        # Note: Socket.IO emit handled in websocket handler
        return new_message

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Ошибка при отправке сообщения"
        )
