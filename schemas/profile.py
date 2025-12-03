from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProfileUpdate(BaseModel):
    """Обновление профиля"""
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None
    profile_background_url: Optional[str] = None

class ProfileOut(BaseModel):
    """Публичный профиль пользователя"""
    id: int
    nickname: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    profile_background_url: Optional[str] = None
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class MyProfileOut(ProfileOut):
    """Мой профиль (с доп. приватной инфой)"""
    email: Optional[str] = None
    
    class Config:
        from_attributes = True