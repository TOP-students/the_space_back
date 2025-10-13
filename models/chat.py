from sqlalchemy import (
    Column,
    String,
    DateTime,
    BigInteger,
    Boolean,
    ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.base import Base


class Chat(Base):
    __tablename__ = "chats"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    type = Column(String(20), default="private")
    user1_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True
    )
    user2_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True
    )
    space_id = Column(
        BigInteger,
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    participants = relationship("ChatParticipant", back_populates="chat")


class ChatParticipant(Base):
    __tablename__ = "chat_participants"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    chat_id = Column(
        BigInteger,
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    chat = relationship("Chat", back_populates="participants")
