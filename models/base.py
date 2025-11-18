from sqlalchemy import create_engine, Column, String, Boolean, DateTime, ForeignKey, BigInteger, Text, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import bcrypt
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

load_dotenv()

# строка подключения к бд
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# хеширование паролей через bcrypt напрямую
def get_password_hash(password: str) -> str:
    """Хеширует пароль"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль"""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    nickname = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255))
    avatar_url = Column(String(500))
    status = Column(String(10), default="offline")
    is_bot = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    bio = Column(Text)  # о себе
    profile_background_url = Column(String(500)) # фон профиля
    display_name = Column(String(100))  # отображаемое имя (может отличаться от nickname)

    user_roles = relationship("UserRole", back_populates="user")

class UserRole(Base):
    __tablename__ = "user_roles"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    role = relationship("Role", back_populates="user_roles")
    user = relationship("User", back_populates="user_roles")

    __table_args__ = (Index('ix_user_roles_user_role', 'user_id', 'role_id'),)

class Chat(Base):
    __tablename__ = "chats"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    type = Column(String(20), default="private")
    user1_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user2_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    space_id = Column(BigInteger, ForeignKey("spaces.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Message(Base):
    __tablename__ = "messages"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, index=True)
    type = Column(String(20), default="text")
    attachment_id = Column(BigInteger, ForeignKey("attachments.id"))
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", foreign_keys=[user_id], lazy="joined")
    
    __table_args__ = (Index('ix_messages_chat_created_at', 'chat_id', 'created_at'),)

class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    message_id = Column(BigInteger, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_type = Column(String(50))
    file_size = Column(BigInteger)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

class Reaction(Base):
    __tablename__ = "reactions"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    message_id = Column(BigInteger, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reaction = Column(String(10), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # связи (опционально)
    user = relationship("User", lazy="joined")
    message = relationship("Message", lazy="joined")

    __table_args__ = (
        Index("ux_reactions_message_user_reaction", "message_id", "user_id", "reaction", unique=True),
    )

class Role(Base):
    __tablename__ = "roles"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    space_id = Column(BigInteger, ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    permissions = Column(JSON)
    color = Column(String(7))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user_roles = relationship("UserRole", back_populates="role")

class Space(Base):
    __tablename__ = "spaces"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    admin_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    background_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ChatParticipant(Base):
    __tablename__ = "chat_participants"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    __table_args__ = (Index('ix_participants_chat_user', 'chat_id', 'user_id'),)

class Ban(Base):
    __tablename__ = "bans"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    banned_by = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    space_id = Column(BigInteger, ForeignKey("spaces.id"), index=True)
    reason = Column(Text)
    until = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index('ix_bans_user_space', 'user_id', 'space_id'),)