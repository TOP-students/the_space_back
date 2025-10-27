from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

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
    
    class Config:
        from_attributes = True

class RoleCreate(BaseModel):
    name: str
    permissions: Optional[List[str]] = None
    color: Optional[str] = None

class RoleOut(BaseModel):
    id: int
    name: str
    permissions: Optional[List[str]] = None
    color: Optional[str] = None

class BanCreate(BaseModel):
    reason: Optional[str] = None
    until: Optional[datetime] = None