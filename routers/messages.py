from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, status, UploadFile, File
from typing import List
from sqlalchemy.orm import Session
import json

from schemas.message import MessageCreate, MessageOut, MessageUpdate
from utils.auth import get_current_user, get_db
from utils.file_upload import FileUploader
from models.base import User, ChatParticipant
from crud.message import MessageRepository
from crud.reaction import ReactionRepository

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
    
    # проверка что пользователь - участник чата
    participant = db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id, 
        ChatParticipant.user_id == current_user.id, 
        ChatParticipant.is_active == True
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник этого чата")
    
    # создание сообщения
    new_message = message_repo.create(
        chat_id, 
        current_user.id, 
        message.content, 
        message.type, 
        message.attachment_id if hasattr(message, 'attachment_id') else None
    )
    
    return new_message

@router.post("/{chat_id}/{message_id}/react")
async def add_reaction(
    chat_id: int,
    message_id: int,
    reaction: str = Query(..., min_length=1, max_length=10),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Добавить реакцию на сообщение"""
    reaction_repo = ReactionRepository(db)
    message_repo = MessageRepository(db)
    
    # проверка что сообщение существует и в правильном чате
    message = message_repo.get_by_id(message_id)
    if not message or message.chat_id != chat_id:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    
    # проверка участника
    participant = db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id,
        ChatParticipant.user_id == current_user.id,
        ChatParticipant.is_active == True
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник этого чата")
    
    # добавляем реакцию (toggle)
    result = reaction_repo.add_reaction(message_id, current_user.id, reaction)
    
    # получаем обновлённые реакции
    all_reactions = reaction_repo.get_message_reactions(message_id)
    
    return {
        "message_id": message_id,
        "reactions": all_reactions
    }

@router.get("/{chat_id}/{message_id}/reactions")
async def get_reactions(
    chat_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить все реакции на сообщение"""
    reaction_repo = ReactionRepository(db)
    message_repo = MessageRepository(db)
    
    # проверка сообщения
    message = message_repo.get_by_id(message_id)
    if not message or message.chat_id != chat_id:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    
    reactions = reaction_repo.get_message_reactions(message_id)
    my_reaction = reaction_repo.get_user_reaction(message_id, current_user.id)
    
    return {
        "message_id": message_id,
        "reactions": reactions,
        "my_reaction": my_reaction
    }

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
    
    # проверка что пользователь - участник чата
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
    
    # проверка что пользователь - участник чата
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

@router.post("/{chat_id}/upload-image", response_model=MessageOut)
async def send_image(
    chat_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отправить изображение"""
    message_repo = MessageRepository(db)
    
    # проверка участника
    participant = db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id,
        ChatParticipant.user_id == current_user.id,
        ChatParticipant.is_active == True
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник этого чата")
    
    # загрузка файла
    file_info = await FileUploader.upload_image(file)
    
    # создание сообщения
    new_message = message_repo.create_with_attachment(
        chat_id,
        current_user.id,
        f"📷 {file.filename}",
        "image",
        file_info
    )
    
    return new_message

@router.post("/{chat_id}/upload-audio", response_model=MessageOut)
async def send_audio(
    chat_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отправить аудио"""
    message_repo = MessageRepository(db)
    
    participant = db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id,
        ChatParticipant.user_id == current_user.id,
        ChatParticipant.is_active == True
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник этого чата")
    
    file_info = await FileUploader.upload_audio(file)
    
    new_message = message_repo.create_with_attachment(
        chat_id,
        current_user.id,
        f"🎵 {file.filename}",
        "audio",
        file_info
    )
    
    return new_message

@router.post("/{chat_id}/upload-document", response_model=MessageOut)
async def send_document(
    chat_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отправить документ"""
    message_repo = MessageRepository(db)
    
    participant = db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id,
        ChatParticipant.user_id == current_user.id,
        ChatParticipant.is_active == True
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник этого чата")
    
    file_info = await FileUploader.upload_document(file)
    
    new_message = message_repo.create_with_attachment(
        chat_id,
        current_user.id,
        f"📄 {file.filename}",
        "file",
        file_info
    )
    
    return new_message