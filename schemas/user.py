from pydantic import BaseModel, field_validator
from typing import Optional
from utils.validators import Validators

class UserCreate(BaseModel):
    nickname: str
    email: Optional[str] = None
    password: str
    
    @field_validator('nickname')
    @classmethod
    def validate_nickname(cls, v):
        is_valid, error = Validators.validate_nickname(v)
        if not is_valid:
            raise ValueError(error)
        return Validators.sanitize_input(v)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v:
            is_valid, error = Validators.validate_email(v)
            if not is_valid:
                raise ValueError(error)
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        is_valid, error = Validators.validate_password(v)
        if not is_valid:
            raise ValueError(error)
        return v

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