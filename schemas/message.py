from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from schemas.attachment import AttachmentOut

class MessageCreate(BaseModel):
    content: str
    type: Optional[str] = "text"
    attachment_id: Optional[int] = None

class MessageUpdate(BaseModel):
    content: str

class UserInfo(BaseModel):
    """Информация о пользователе для сообщения"""
    id: int
    nickname: str
    avatar_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class MessageOut(BaseModel):
    id: int
    chat_id: int
    user_id: int
    content: Optional[str]
    type: str
    created_at: datetime
    user: Optional[UserInfo] = None
    user_nickname: Optional[str] = None  # для совместимости с фронтендом
    attachment: AttachmentOut | None = None
    reactions: Optional[list] = None
    my_reaction: Optional[str] = None

    class Config:
        from_attributes = True