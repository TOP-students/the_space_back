from typing import Optional, List
from pydantic import BaseModel


class RoleCreate(BaseModel):
    name: str
    permissions: Optional[List[str]] = None
    color: Optional[str] = None


class RoleOut(BaseModel):
    id: int
    name: str
    permissions: Optional[List[str]] = None
    color: Optional[str] = None
