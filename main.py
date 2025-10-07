from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy import BigInteger, Text, JSON, or_, asc, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, constr
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import socketio
import json
import os
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()  # Загрузка .env

# настройки
SECRET_KEY = os.getenv("SECRET_KEY", "your-fallback-secret-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# коннект с PostgreSQL (async)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/chat_db")  # Требует asyncpg
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# хэширование паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Chat App API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Инициализация Socket.IO сервера
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*"
)

# Оборачиваем FastAPI в ASGI-приложение Socket.IO
socket_app = socketio.ASGIApp(sio, app)

# Хранилища подключений
active_users: dict[int, str] = {}       # {user_id: sid}
user_rooms: dict[int, set[int]] = {}    # {user_id: {chat_ids}}


# SQLAlchemy модели
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
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Chat(Base):
    __tablename__ = "chats"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    type = Column(String(20), default="private")
    user1_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    user2_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    space_id = Column(BigInteger, ForeignKey("spaces.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    participants = relationship("ChatParticipant", back_populates="chat")


class Message(Base):
    __tablename__ = "messages"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
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
    message_id = Column(BigInteger, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_type = Column(String(50))
    file_size = Column(BigInteger)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class Role(Base):
    __tablename__ = "roles"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    space_id = Column(BigInteger, ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False)
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
    admin_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    background_url = Column(String(500))
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatParticipant(Base):
    __tablename__ = "chat_participants"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    chat = relationship("Chat", back_populates="participants")


class Ban(Base):
    __tablename__ = "bans"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    banned_by = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    space_id = Column(BigInteger, ForeignKey("spaces.id"))
    reason = Column(Text)
    until = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserRole(Base):
    __tablename__ = "user_roles"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    role = relationship("Role", back_populates="user_roles")


# Pydantic модели
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


class MessageCreate(BaseModel):
    content: constr(min_length=1, max_length=5000)
    type: Optional[str] = "text"
    attachment_id: Optional[int] = None


class MessageOut(BaseModel):
    id: int
    chat_id: int
    user_id: int
    content: Optional[str]
    type: str
    created_at: datetime


class RoleCreate(BaseModel):
    name: str
    permissions: Optional[List[str]] = None
    color: Optional[str]


class RoleOut(BaseModel):
    id: int
    name: str
    permissions: Optional[List[str]]
    color: Optional[str]


class SpaceCreate(BaseModel):
    name: str
    description: Optional[str]
    background_url: Optional[str]


class SpaceOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    admin_id: int
    chat_id: Optional[int]


class BanCreate(BaseModel):
    reason: Optional[str]
    until: Optional[datetime]


class PrivateChatCreate(BaseModel):
    user2_id: int


class ChatResponse(BaseModel):
    chat_id: int
    message: str


# зависимости
async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_async_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невозможно валидировать токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    result = await db.execute(select(User).filter(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


# функция проверки прав (async версия)
async def check_permissions(db: AsyncSession, user_id: int, space_id: int, required_permission: str, space_admin_id: int) -> bool:
    if user_id == space_admin_id:
        return True
    result = await db.execute(select(UserRole).join(Role).filter(
        UserRole.user_id == user_id, Role.space_id == space_id
    ))
    user_role = result.scalar_one_or_none()
    if not user_role:
        return False
    permissions = user_role.role.permissions
    if isinstance(permissions, str):
        permissions = json.loads(permissions)
    permissions = permissions or []
    return required_permission in permissions or "admin" in permissions


# утилиты (хэширование и JWT)
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expires_delta = expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Socket.IO события для real-time чата (full async)
@sio.event
async def connect(sid, environ, auth):
    token = None
    try:
        token = auth.get("token")
    except Exception:
        pass

    if not token:
        await sio.disconnect(sid)
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except JWTError:
        await sio.disconnect(sid)
        return

    active_users[user_id] = sid
    user_rooms[user_id] = set()

    # Обновляем статус в DB
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.status = "online"
            await session.commit()

    print(f"Пользователь {user_id} подключился (SID={sid})")

    await sio.emit("user_status_changed", {
        "user_id": user_id,
        "status": "online",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@sio.event
async def disconnect(sid):
    user_id = next((uid for uid, s in active_users.items() if s == sid), None)
    if not user_id:
        return
    del active_users[user_id]
    user_rooms.pop(user_id, None)

    # Обновляем статус в DB
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.status = "offline"
            await session.commit()

    print(f"Пользователь {user_id} отключился")

    await sio.emit("user_status_changed", {
        "user_id": user_id,
        "status": "offline",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@sio.on("join_room")
async def handle_join_room(sid, data):
    chat_id = data.get("chat_id")
    if not chat_id:
        await sio.emit("error", {"message": "chat_id обязателен"}, to=sid)
        return

    user_id = next((uid for uid, s in active_users.items() if s == sid), None)
    if not user_id:
        return

    # Синхронизация с DB
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ChatParticipant).filter(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == user_id))
        existing = result.scalar_one_or_none()
        if existing and existing.is_active:
            pass
        elif existing:
            existing.is_active = True
        else:
            new_participant = ChatParticipant(chat_id=chat_id, user_id=user_id, is_active=True)
            session.add(new_participant)
        await session.commit()

    room = f"chat_{chat_id}"
    await sio.enter_room(sid, room)
    user_rooms[user_id].add(chat_id)

    print(f"👥 Пользователь {user_id} вошёл в комнату {chat_id}")

    await sio.emit("user_joined", {
        "chat_id": chat_id,
        "user_id": user_id
    }, room=room)


@sio.on("leave_room")
async def handle_leave_room(sid, data):
    chat_id = data.get("chat_id")
    if not chat_id:
        return
    user_id = next((uid for uid, s in active_users.items() if s == sid), None)
    if not user_id:
        return

    # Синхронизация с DB
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ChatParticipant).filter(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == user_id))
        participant = result.scalar_one_or_none()
        if participant:
            participant.is_active = False
            await session.commit()

    await sio.leave_room(sid, f"chat_{chat_id}")
    user_rooms[user_id].discard(chat_id)

    await sio.emit("user_left", {
        "chat_id": chat_id,
        "user_id": user_id
    }, room=f"chat_{chat_id}")


@sio.on("send_message")
async def handle_send_message(sid, data):
    user_id = next((uid for uid, s in active_users.items() if s == sid), None)
    if not user_id:
        return

    chat_id = data.get("chat_id")
    content = data.get("content")
    msg_type = data.get("type", "text")

    if not chat_id or not content:
        await sio.emit("error", {"message": "chat_id и content обязательны"}, to=sid)
        return

    # Проверка участия
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ChatParticipant).filter(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == user_id, ChatParticipant.is_active == True))
        participant = result.scalar_one_or_none()
        if not participant:
            await sio.emit("error", {"message": "Вы не участник чата"}, to=sid)
            return

        new_msg = Message(
            chat_id=chat_id,
            user_id=user_id,
            content=content,
            type=msg_type,
            created_at=datetime.now(timezone.utc)
        )
        session.add(new_msg)
        await session.commit()
        await session.refresh(new_msg)

    msg_data = {
        "chat_id": chat_id,
        "message": {
            "id": new_msg.id,
            "user_id": user_id,
            "content": content,
            "type": msg_type,
            "created_at": new_msg.created_at.isoformat()
        }
    }

    await sio.emit("new_message", msg_data, room=f"chat_{chat_id}")


# эндпоинты (все async)
@app.post("/logout")
async def logout(request: Request):
    return {"message": "Успешный выход (токен истёк)"}


@app.post("/register", response_model=UserOut)
async def register(user: UserCreate, db=Depends(get_async_db)):
    result = await db.execute(select(User).filter(User.nickname == user.nickname))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Никнейм уже занят")
    if user.email:
        result = await db.execute(select(User).filter(User.email == user.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email уже используется")
    hashed_password = get_password_hash(user.password)
    new_user = User(nickname=user.nickname, email=user.email, password_hash=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@app.post("/token", response_model=Token)
@limiter.limit("5/minute")
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_async_db)):
    result = await db.execute(select(User).filter(User.nickname == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный никнейм или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/spaces", response_model=SpaceOut)
async def create_space(space: SpaceCreate, current_user: User = Depends(get_current_user), db=Depends(get_async_db)):
    new_space = Space(name=space.name, description=space.description, admin_id=current_user.id, background_url=space.background_url)
    db.add(new_space)
    await db.flush()
    chat = Chat(type="group", space_id=new_space.id)
    db.add(chat)
    await db.flush()
    participant = ChatParticipant(chat_id=chat.id, user_id=current_user.id, is_active=True)
    db.add(participant)
    new_space.chat_id = chat.id
    await db.commit()
    await db.refresh(new_space)
    return new_space


@app.post("/spaces/{space_id}/roles", response_model=RoleOut)
async def create_role(space_id: int, role: RoleCreate, current_user: User = Depends(get_current_user), db=Depends(get_async_db)):
    result = await db.execute(select(Space).filter(Space.id == space_id))
    space = result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")
    if not await check_permissions(db, current_user.id, space_id, "assign_role", space.admin_id):
        raise HTTPException(status_code=403, detail="У вас нет прав на создание ролей")

    new_role = Role(space_id=space_id, name=role.name, permissions=role.permissions, color=role.color)
    db.add(new_role)
    await db.commit()
    await db.refresh(new_role)
    return new_role


@app.post("/chats", response_model=ChatResponse)
async def create_private_chat(chat_data: PrivateChatCreate, current_user: User = Depends(get_current_user), db=Depends(get_async_db)):
    if chat_data.user2_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя создать чат с самим собой")
    result = await db.execute(select(User).filter(User.id == chat_data.user2_id))
    user2 = result.scalar_one_or_none()
    if not user2:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Проверяем, нет ли уже чата
    query = select(Chat).filter(
        or_(
            (Chat.user1_id == current_user.id) & (Chat.user2_id == chat_data.user2_id),
            (Chat.user1_id == chat_data.user2_id) & (Chat.user2_id == current_user.id)
        )
    )
    result = await db.execute(query)
    existing_chat = result.scalar_one_or_none()
    if existing_chat:
        raise HTTPException(status_code=400, detail="Чат уже существует")

    new_chat = Chat(type="private", user1_id=current_user.id, user2_id=chat_data.user2_id)
    db.add(new_chat)
    await db.flush()
    participant1 = ChatParticipant(chat_id=new_chat.id, user_id=current_user.id, is_active=True)
    participant2 = ChatParticipant(chat_id=new_chat.id, user_id=chat_data.user2_id, is_active=True)
    db.add_all([participant1, participant2])
    await db.commit()
    await db.refresh(new_chat)
    return ChatResponse(chat_id=new_chat.id, message="Private чат создан")


@app.post("/spaces/{space_id}/join")
async def join_space(space_id: int, current_user: User = Depends(get_current_user), db=Depends(get_async_db)):
    result = await db.execute(select(Space).filter(Space.id == space_id))
    space = result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")

    # Проверка бана
    ban_query = select(Ban).filter(
        Ban.user_id == current_user.id,
        Ban.space_id == space_id,
        or_(Ban.until > datetime.now(timezone.utc), Ban.until.is_(None))
    )
    result = await db.execute(ban_query)
    active_ban = result.scalar_one_or_none()
    if active_ban:
        raise HTTPException(status_code=403, detail="Вы забанены в этом пространстве")

    # Получаем чат пространства
    result = await db.execute(select(Chat).filter(Chat.space_id == space_id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат для пространства не найден")

    # Проверяем, не участник ли уже
    result = await db.execute(select(ChatParticipant).filter(ChatParticipant.chat_id == chat.id, ChatParticipant.user_id == current_user.id))
    existing = result.scalar_one_or_none()
    if existing and existing.is_active:
        raise HTTPException(status_code=400, detail="Вы уже участник")

    if existing:
        existing.is_active = True
    else:
        new_participant = ChatParticipant(chat_id=chat.id, user_id=current_user.id, is_active=True)
        db.add(new_participant)

    await db.commit()
    return {"message": "Успешно присоединены к пространству"}


@app.get("/spaces/{space_id}/participants", response_model=List[UserOut])
async def get_participants(space_id: int, current_user: User = Depends(get_current_user), db=Depends(get_async_db)):
    result = await db.execute(select(Space).filter(Space.id == space_id))
    space = result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")

    result = await db.execute(select(Chat).filter(Chat.space_id == space_id))
    chat = result.scalar_one_or_none()
    if not chat:
        return []

    query = select(User).join(ChatParticipant).filter(ChatParticipant.chat_id == chat.id, ChatParticipant.is_active == True)
    result = await db.execute(query)
    participants = result.scalars().all()
    return participants


@app.delete("/spaces/{space_id}/kick/{user_id}")
async def kick_user(space_id: int, user_id: int, current_user: User = Depends(get_current_user), db=Depends(get_async_db)):
    result = await db.execute(select(Space).filter(Space.id == space_id))
    space = result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")
    if not await check_permissions(db, current_user.id, space_id, "kick", space.admin_id):
        raise HTTPException(status_code=403, detail="У вас нет прав на кик")

    result = await db.execute(select(Chat).filter(Chat.space_id == space_id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    result = await db.execute(select(ChatParticipant).filter(ChatParticipant.chat_id == chat.id, ChatParticipant.user_id == user_id))
    participant = result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=404, detail="Пользователь не найден в пространстве")

    participant.is_active = False
    await db.commit()
    return {"message": "Пользователь успешно кикнут"}


@app.post("/spaces/{space_id}/ban/{user_id}")
async def ban_user(space_id: int, user_id: int, ban_data: BanCreate, current_user: User = Depends(get_current_user), db=Depends(get_async_db)):
    result = await db.execute(select(Space).filter(Space.id == space_id))
    space = result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")
    if not await check_permissions(db, current_user.id, space_id, "ban", space.admin_id):
        raise HTTPException(status_code=403, detail="У вас нет прав на бан")

    new_ban = Ban(user_id=user_id, banned_by=current_user.id, space_id=space_id, reason=ban_data.reason, until=ban_data.until)
    db.add(new_ban)

    # Деактивируем участие
    result = await db.execute(select(Chat).filter(Chat.space_id == space_id))
    chat = result.scalar_one_or_none()
    if chat:
        result = await db.execute(select(ChatParticipant).filter(ChatParticipant.chat_id == chat.id, ChatParticipant.user_id == user_id))
        participant = result.scalar_one_or_none()
        if participant:
            participant.is_active = False

    await db.commit()
    return {"message": "Пользователь успешно забанен"}


@app.post("/spaces/{space_id}/assign-role/{user_id}/{role_id}")
async def assign_role(space_id: int, user_id: int, role_id: int, current_user: User = Depends(get_current_user), db=Depends(get_async_db)):
    result = await db.execute(select(Space).filter(Space.id == space_id))
    space = result.scalar_one_or_none()
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")
    if not await check_permissions(db, current_user.id, space_id, "assign_role", space.admin_id):
        raise HTTPException(status_code=403, detail="У вас нет прав на назначение ролей")

    result = await db.execute(select(Role).filter(Role.id == role_id, Role.space_id == space_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Роль не найдена")

    result = await db.execute(select(UserRole).filter(UserRole.user_id == user_id, UserRole.role_id == role_id))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Роль уже назначена")

    new_user_role = UserRole(user_id=user_id, role_id=role_id)
    db.add(new_user_role)
    await db.commit()
    return {"message": "Роль успешно назначена"}


@app.post("/chats/{chat_id}/messages", response_model=MessageOut)
@limiter.limit("10/minute")
async def send_message(chat_id: int, message: MessageCreate, request: Request, current_user: User = Depends(get_current_user), db=Depends(get_async_db)):
    result = await db.execute(select(Chat).filter(Chat.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    result = await db.execute(select(ChatParticipant).filter(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == current_user.id, ChatParticipant.is_active == True))
    participant = result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник чата")

    new_message = Message(chat_id=chat_id, user_id=current_user.id, content=message.content, type=message.type, attachment_id=message.attachment_id)
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)

    # Emit через Socket.IO
    msg_data = {
        "chat_id": chat_id,
        "message": {
            "id": new_message.id,
            "user_id": current_user.id,
            "content": message.content,
            "type": message.type,
            "created_at": new_message.created_at.isoformat()
        }
    }
    await sio.emit("new_message", msg_data, room=f"chat_{chat_id}")

    return new_message


@app.get("/chats/{chat_id}/messages", response_model=List[MessageOut])
async def get_messages(chat_id: int, limit: int = 50, current_user: User = Depends(get_current_user), db=Depends(get_async_db)):
    result = await db.execute(select(Chat).filter(Chat.id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    result = await db.execute(select(ChatParticipant).filter(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == current_user.id, ChatParticipant.is_active == True))
    participant = result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник чата")

    query = select(Message).filter(Message.chat_id == chat_id, Message.is_deleted == False).order_by(asc(Message.created_at)).limit(limit)
    result = await db.execute(query)
    messages = result.scalars().all()
    return messages


# Startup event для создания таблиц
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Запуск
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
