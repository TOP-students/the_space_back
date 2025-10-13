from sqlalchemy import Column, Text, String, DateTime, BigInteger, ForeignKey
from sqlalchemy.sql import func

from models.base import Base


class Space(Base):
    __tablename__ = "spaces"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    admin_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    background_url = Column(String(500))
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
