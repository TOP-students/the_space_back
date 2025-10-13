from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class SpaceCreate(BaseModel):
    name: str
    description: Optional[str]
    background_url: Optional[str]

class SpaceOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    admin_id: int
    chat_id: Optional[int]

class RoleCreate(BaseModel):
    name: str
    permissions: Optional[List[str]] = None
    color: Optional[str]

class RoleOut(BaseModel):
    id: int
    name: str
    permissions: Optional[List[str]]
    color: Optional[str]

class BanCreate(BaseModel):
    reason: Optional[str]
    until: Optional[datetime]