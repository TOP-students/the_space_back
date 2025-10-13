from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MessageCreate(BaseModel):
    content: str
    type: Optional[str] = "text"
    attachment_id: Optional[int] = None

class MessageUpdate(BaseModel):
    content: str

class MessageOut(BaseModel):
    id: int
    chat_id: int
    user_id: int
    content: Optional[str]
    type: str
    created_at: datetime