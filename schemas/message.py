from typing import Optional
from datetime import datetime
from pydantic import BaseModel, constr


class MessageCreate(BaseModel):
    content: constr(min_length=1, max_length=5000)
    type: Optional[str] = "text"
    attachment_id: Optional[int] = None


class MessageOut(BaseModel):
    id: int
    chat_id: int
    user_id: int
    content: Optional[str] = None
    type: str
    created_at: datetime
