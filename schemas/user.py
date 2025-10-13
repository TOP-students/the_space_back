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

class Token(BaseModel):
    access_token: str
    token_type: str