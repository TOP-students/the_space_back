from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class SpaceCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    background_url: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        from utils.validators import Validators
        is_valid, error = Validators.validate_space_name(v)
        if not is_valid:
            raise ValueError(error)
        return Validators.sanitize_input(v)
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if v:
            from utils.validators import Validators
            is_valid, error = Validators.validate_space_description(v)
            if not is_valid:
                raise ValueError(error)
            return Validators.sanitize_input(v)
        return v

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

    class Config:
        from_attributes = True

class BanCreate(BaseModel):
    reason: Optional[str] = None
    until: Optional[datetime] = None