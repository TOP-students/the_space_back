from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List
from sqlalchemy.orm import Session

from schemas.message import MessageCreate, MessageOut, MessageUpdate
from utils.auth import get_current_user, get_db
from models.base import User, ChatParticipant
from crud.message import MessageRepository

router = APIRouter()

# FastAPI WebSocket код удалён - используем Socket.IO
# См. utils/socketio_handlers.py для realtime функциональности

@router.post("/{chat_id}", response_model=MessageOut)
def send_message(
    chat_id: int, 
    message: MessageCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отправить сообщение в чат"""
    message_repo = MessageRepository(db)
    
    participant = db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id, 
        ChatParticipant.user_id == current_user.id, 
        ChatParticipant.is_active == True
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник этого чата")
    
    new_message = message_repo.create(
        chat_id,
        current_user.id,
        message.content,
        message.type,
        message.attachment_id if hasattr(message, 'attachment_id') else None
    )

    # Broadcast теперь происходит через Socket.IO в utils/socketio_handlers.py

    return new_message

@router.get("/{chat_id}", response_model=List[MessageOut])
def get_messages(
    chat_id: int, 
    limit: int = Query(50, ge=1, le=100), 
    offset: int = Query(0, ge=0), 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить сообщения из чата"""
    message_repo = MessageRepository(db)
    
    participant = db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id, 
        ChatParticipant.user_id == current_user.id, 
        ChatParticipant.is_active == True
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник этого чата")
    
    messages = message_repo.get_by_chat(chat_id, limit, offset)
    return messages

@router.get("/{chat_id}/search", response_model=List[MessageOut])
def search_messages(
    chat_id: int, 
    q: str = Query(..., min_length=1), 
    limit: int = Query(50, ge=1, le=100), 
    offset: int = Query(0, ge=0), 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Поиск сообщений в чате"""
    message_repo = MessageRepository(db)
    
    participant = db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id, 
        ChatParticipant.user_id == current_user.id, 
        ChatParticipant.is_active == True
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник этого чата")
    
    messages = message_repo.search_by_chat(chat_id, q, limit, offset)
    return messages

@router.patch("/{chat_id}/{message_id}", response_model=MessageOut)
def update_message(
    chat_id: int, 
    message_id: int, 
    update_data: MessageUpdate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Редактировать сообщение"""
    message_repo = MessageRepository(db)
    
    message = message_repo.get_by_id(message_id)
    if not message or message.chat_id != chat_id or message.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Сообщение не найдено или недоступно")
    
    updated_message = message_repo.update(message_id, update_data.content, current_user.id)
    if not updated_message:
        raise HTTPException(status_code=400, detail="Не удалось обновить сообщение")
    
    return updated_message

@router.delete("/{chat_id}/{message_id}")
def delete_message(
    chat_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить сообщение"""
    message_repo = MessageRepository(db)
    
    message = message_repo.get_by_id(message_id)
    if not message or message.chat_id != chat_id or message.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Сообщение не найдено или недоступно")
    
    deleted_message = message_repo.delete(message_id, current_user.id)
    if not deleted_message:
        raise HTTPException(status_code=400, detail="Не удалось удалить сообщение")
    
    return {"message": "Сообщение удалено"}