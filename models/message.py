from sqlalchemy import (
    Column,
    Text,
    String,
    DateTime,
    BigInteger,
    Boolean,
    ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.base import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    chat_id = Column(
        BigInteger,
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    content = Column(Text)
    type = Column(String(20), default="text")
    attachment_id = Column(BigInteger, ForeignKey("attachments.id"))
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    chat = relationship("Chat")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    message_id = Column(
        BigInteger,
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False
    )
    file_url = Column(String(500), nullable=False)
    file_type = Column(String(50))
    file_size = Column(BigInteger)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
