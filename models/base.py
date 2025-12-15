from sqlalchemy import create_engine, Column, String, Boolean, DateTime, ForeignKey, Integer, BigInteger, Text, JSON, Index
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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/chat_app")

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

    # user_roles = relationship("UserRole", back_populates="user")

class UserRole(Base):
    __tablename__ = "user_roles"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index('ix_user_roles_user_role', 'user_id', 'role_id'),)

class UserActivity(Base):
    __tablename__ = "user_activity"
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    last_seen = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status = Column(String(20), default="offline")  # online, offline, away, dnd
    is_active = Column(Boolean, default=False)
    device_info = Column(String(255))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Chat(Base):
    __tablename__ = "chats"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    type = Column(String(20), default="private")
    user1_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user2_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    space_id = Column(BigInteger, ForeignKey("spaces.id", ondelete="CASCADE"))
    avatar_url = Column(String(500))
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
    attachment = relationship("Attachment", foreign_keys=[attachment_id], lazy="joined")

    __table_args__ = (Index('ix_messages_chat_created_at', 'chat_id', 'created_at'),)

class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    message_id = Column(BigInteger, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_type = Column(String(50))
    file_size = Column(BigInteger)
    file_name = Column(String(255))
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
    permissions = Column(JSON)  # список разрешений
    color = Column(String(7))
    priority = Column(Integer, default=10)  # выше = больше прав
    is_system = Column(Boolean, default=False)  # системную роль нельзя удалить
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Space(Base):
    __tablename__ = "spaces"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    admin_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    background_url = Column(String(500))
    avatar_url = Column(String(500))
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

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # mention, reply, space_invite, role_change
    title = Column(String(255), nullable=False)
    content = Column(Text)
    related_message_id = Column(BigInteger, ForeignKey("messages.id", ondelete="CASCADE"))
    related_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    related_space_id = Column(BigInteger, ForeignKey("spaces.id", ondelete="CASCADE"))
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Mention(Base):
    __tablename__ = "mentions"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    message_id = Column(BigInteger, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    mentioned_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index('ix_mentions_message_user', 'message_id', 'mentioned_user_id'),)

class StickerPack(Base):
    __tablename__ = "sticker_packs"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    author_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    thumbnail_url = Column(String(500))
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Sticker(Base):
    __tablename__ = "stickers"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    pack_id = Column(BigInteger, ForeignKey("sticker_packs.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100))
    image_url = Column(String(500), nullable=False)
    emoji_shortcode = Column(String(50))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserStickerPack(Base):
    __tablename__ = "user_sticker_packs"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    pack_id = Column(BigInteger, ForeignKey("sticker_packs.id", ondelete="CASCADE"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index('ix_user_sticker_pack', 'user_id', 'pack_id'),)