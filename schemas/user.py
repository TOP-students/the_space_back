from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    nickname: str
    email: Optional[str]
    password: str

class UserOut(BaseModel):
    id: int
    nickname: str
    email: Optional[str]
    status: str
    avatar_url: Optional[str] = None
    profile_background_url: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str