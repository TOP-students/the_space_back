from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from utils.auth import get_current_user, get_db
from models.base import User
from crud.activity import ActivityRepository

router = APIRouter()

@router.get("/my-status")
async def get_my_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить мой статус"""
    activity_repo = ActivityRepository(db)
    status_info = activity_repo.get_user_status(current_user.id)
    
    return {
        "user_id": current_user.id,
        "nickname": current_user.nickname,
        **status_info
    }

@router.post("/set-status")
async def set_status(
    status: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Установить статус (online, offline, away, dnd)"""
    valid_statuses = ["online", "offline", "away", "dnd"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Некорректный статус. Допустимые: {', '.join(valid_statuses)}"
        )
    
    activity_repo = ActivityRepository(db)
    activity_repo.set_status(current_user.id, status)
    
    return {"message": f"Статус изменён на {status}"}

@router.get("/user/{user_id}")
async def get_user_status(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статус другого пользователя"""
    activity_repo = ActivityRepository(db)
    
    # проверка что пользователь существует
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    status_info = activity_repo.get_user_status(user_id)
    
    return {
        "user_id": user.id,
        "nickname": user.nickname,
        "display_name": user.display_name,
        **status_info
    }

@router.get("/online")
async def get_online_users(
    space_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список онлайн пользователей"""
    activity_repo = ActivityRepository(db)
    
    online_users = activity_repo.get_online_users(space_id)
    
    return {
        "count": len(online_users),
        "users": online_users
    }

@router.post("/heartbeat")
async def heartbeat(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Heartbeat для поддержания онлайн статуса"""
    activity_repo = ActivityRepository(db)
    activity_repo.update_activity(current_user.id, status="online")
    
    return {"message": "Activity updated"}