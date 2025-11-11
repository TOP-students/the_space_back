from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from schemas.profile import ProfileUpdate, ProfileOut, MyProfileOut
from utils.auth import get_current_user, get_db
from models.base import User

router = APIRouter()

@router.get("/me", response_model=MyProfileOut)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Получить свой профиль"""
    return current_user

@router.patch("/me", response_model=MyProfileOut)
async def update_my_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить свой профиль"""
    
    # Обновляем только переданные поля
    if profile_data.display_name is not None:
        current_user.display_name = profile_data.display_name
    
    if profile_data.bio is not None:
        current_user.bio = profile_data.bio
    
    if profile_data.avatar_url is not None:
        current_user.avatar_url = profile_data.avatar_url
    
    if profile_data.profile_background_url is not None:
        current_user.profile_background_url = profile_data.profile_background_url
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.get("/{user_id}", response_model=ProfileOut)
async def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить профиль пользователя по ID"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    return user

@router.get("/nickname/{nickname}", response_model=ProfileOut)
async def get_user_profile_by_nickname(
    nickname: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить профиль пользователя по никнейму"""
    user = db.query(User).filter(User.nickname == nickname).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    return user