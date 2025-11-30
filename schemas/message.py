from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from schemas.attachment import AttachmentOut

class MessageCreate(BaseModel):
    content: str
    type: Optional[str] = "text"
    attachment_id: Optional[int] = None
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        from utils.validators import Validators
        is_valid, error = Validators.validate_message_content(v)
        if not is_valid:
            raise ValueError(error)
        return Validators.sanitize_input(v)
    
    @field_validator('attachment_id')
    @classmethod
    def validate_attachment_id(cls, v):
        # преобразуем 0 в None
        if v == 0:
            return None
        return v

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