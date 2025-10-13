from typing import Optional
from pydantic import BaseModel


class SpaceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    background_url: Optional[str] = None


class SpaceOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    admin_id: int
    chat_id: Optional[int] = None
