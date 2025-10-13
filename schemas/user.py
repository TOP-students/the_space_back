from typing import Optional
from pydantic import BaseModel


class UserCreate(BaseModel):
    nickname: str
    email: Optional[str] = None
    password: str


class UserOut(BaseModel):
    id: int
    nickname: str
    email: Optional[str] = None
    status: str
