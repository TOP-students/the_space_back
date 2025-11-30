from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from utils.auth import get_current_user, get_db
from models.base import User
from crud.notification import NotificationRepository

router = APIRouter()

@router.get("/")
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить уведомления"""
    notification_repo = NotificationRepository(db)
    notifications = notification_repo.get_user_notifications(
        current_user.id, 
        unread_only=unread_only, 
        limit=limit
    )
    
    return [{
        "id": n.id,
        "type": n.type,
        "title": n.title,
        "content": n.content,
        "is_read": n.is_read,
        "created_at": n.created_at,
        "related_message_id": n.related_message_id,
        "related_user_id": n.related_user_id,
        "related_space_id": n.related_space_id
    } for n in notifications]

@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить количество непрочитанных уведомлений"""
    notification_repo = NotificationRepository(db)
    count = notification_repo.get_unread_count(current_user.id)
    
    return {"unread_count": count}

@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Пометить уведомление как прочитанное"""
    notification_repo = NotificationRepository(db)
    success = notification_repo.mark_as_read(notification_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")
    
    return {"message": "Уведомление помечено как прочитанное"}

@router.post("/mark-all-read")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Пометить все уведомления как прочитанные"""
    notification_repo = NotificationRepository(db)
    notification_repo.mark_all_as_read(current_user.id)
    
    return {"message": "Все уведомления помечены как прочитанные"}