from sqlalchemy import Column, String, Boolean, DateTime, BigInteger
from sqlalchemy.sql import func

from models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    nickname = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True)
    password_hash = Column(String(255))
    avatar_url = Column(String(500))
    status = Column(String(10), default="offline")
    is_bot = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
