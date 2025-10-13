from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger, Text, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import json
import os
from crud.user import UserRepository
from crud.space import SpaceRepository
from crud.message import MessageRepository
from crud.role import RoleRepository
from crud.ban import BanRepository

# настройки
SECRET_KEY = ""
ALGORITHM = ""
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# подключение к PostgreSQL
DATABASE_URL = "postgresql://user:password@localhost/chat_app"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# хэширование и OAuth2
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="Chat App API")

# Модели SQLAlchemy (+ индексы)
class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    nickname = Column(String(50), unique=True, index=True, nullable=False)  # Индекс на nickname
    email = Column(String(255), unique=True, index=True)
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
    user1_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user2_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Message(Base):
    __tablename__ = "messages"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, index=True)  # индекс на content для поиска
    type = Column(String(20), default="text")
    attachment_id = Column(BigInteger, ForeignKey("attachments.id"))
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index('ix_messages_chat_created_at', 'chat_id', 'created_at'),)  # композитный индекс

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
    space_id = Column(BigInteger, ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    permissions = Column(JSON)
    color = Column(String(7))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

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

class UserRole(Base):
    __tablename__ = "user_roles"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index('ix_user_roles_user_role', 'user_id', 'role_id'),)

# Pydantic модели (для пагинации и поиска)
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
    content: str
    type: Optional[str] = "text"
    attachment_id: Optional[int] = None

class MessageUpdate(BaseModel):
    content: str

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

# зависимости (для CRUD)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_repo(db=Depends(get_db)):
    return UserRepository(db)

def get_space_repo(db=Depends(get_db)):
    return SpaceRepository(db)

def get_message_repo(db=Depends(get_db)):
    return MessageRepository(db)

def get_role_repo(db=Depends(get_db)):
    return RoleRepository(db)

def get_ban_repo(db=Depends(get_db)):
    return BanRepository(db)

async def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
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
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user

# функция проверки прав (под CRUD)
def check_permissions(db, user_id: int, space_id: int, required_permission: str, role_repo: RoleRepository) -> bool:
    permissions = role_repo.get_permissions(user_id, space_id)
    return required_permission in permissions or "admin" in permissions

# утилиты
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# WebSocket менеджер
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, chat_id: int):
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = []
        self.active_connections[chat_id].append(websocket)

    def disconnect(self, websocket: WebSocket, chat_id: int):
        self.active_connections[chat_id].remove(websocket)

    async def broadcast(self, message: str, chat_id: int):
        for connection in self.active_connections.get(chat_id, []):
            await connection.send_text(message)

manager = ConnectionManager()

# эндпоинты (под CRUD)
@app.post("/register", response_model=UserOut)
def register(user: UserCreate, user_repo: UserRepository = Depends(get_user_repo)):
    if user_repo.get_by_nickname(user.nickname):
        raise HTTPException(status_code=400, detail="Никнейм уже занят")
    if user.email and user_repo.get_by_email(user.email):
        raise HTTPException(status_code=400, detail="Email уже используется")
    new_user = user_repo.create(user.nickname, user.email or None, user.password)
    return new_user

@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), user_repo: UserRepository = Depends(get_user_repo)):
    user = user_repo.get_by_nickname(form_data.username)
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
def create_space(space: SpaceCreate, current_user: User = Depends(get_current_user), space_repo: SpaceRepository = Depends(get_space_repo)):
    new_space = space_repo.create(space.name, space.description or None, current_user.id, space.background_url or None)
    return new_space

@app.post("/spaces/{space_id}/join")
def join_space(space_id: int, current_user: User = Depends(get_current_user), space_repo: SpaceRepository = Depends(get_space_repo), ban_repo: BanRepository = Depends(get_ban_repo)):
    if ban_repo.is_active(current_user.id, space_id):
        raise HTTPException(status_code=403, detail="Вы забанены в этом пространстве")
    space_repo.join(space_id, current_user.id)
    return {"message": "Успешно присоединены к пространству"}

@app.get("/spaces/{space_id}/participants", response_model=List[UserOut])
def get_participants(space_id: int, current_user: User = Depends(get_current_user), space_repo: SpaceRepository = Depends(get_space_repo)):
    participants = space_repo.get_participants(space_id)
    return participants

@app.delete("/spaces/{space_id}/kick/{user_id}")
def kick_user(space_id: int, user_id: int, current_user: User = Depends(get_current_user), space_repo: SpaceRepository = Depends(get_space_repo), role_repo: RoleRepository = Depends(get_role_repo)):
    if not check_permissions(None, current_user.id, space_id, "kick", role_repo):  # db=None, т.к. используем repo
        raise HTTPException(status_code=403, detail="У вас нет прав на кик")
    space_repo.kick(space_id, user_id)
    return {"message": "Пользователь успешно кикнут"}

@app.post("/spaces/{space_id}/ban/{user_id}")
def ban_user(space_id: int, user_id: int, ban_data: BanCreate, current_user: User = Depends(get_current_user), ban_repo: BanRepository = Depends(get_ban_repo), role_repo: RoleRepository = Depends(get_role_repo)):
    if not check_permissions(None, current_user.id, space_id, "ban", role_repo):
        raise HTTPException(status_code=403, detail="У вас нет прав на бан")
    ban_repo.create(user_id, current_user.id, space_id, ban_data.reason or None, ban_data.until)
    # деактивация участия через space_repo.kick
    space_repo = SpaceRepository(ban_repo.db)  # временный инстанс для kick
    space_repo.kick(space_id, user_id)
    return {"message": "Пользователь успешно забанен"}

@app.post("/spaces/{space_id}/assign-role/{user_id}/{role_id}")
def assign_role(space_id: int, user_id: int, role_id: int, current_user: User = Depends(get_current_user), role_repo: RoleRepository = Depends(get_role_repo)):
    if not check_permissions(None, current_user.id, space_id, "assign_role", role_repo):
        raise HTTPException(status_code=403, detail="У вас нет прав на назначение ролей")
    role_repo.assign_to_user(user_id, role_id)
    return {"message": "Роль успешно назначена"}

# сообщения (с пагинацией)
@app.post("/chats/{chat_id}/messages", response_model=MessageOut)
def send_message(chat_id: int, message: MessageCreate, current_user: User = Depends(get_current_user), message_repo: MessageRepository = Depends(get_message_repo)):
    # проверка участия (через db)
    participant = message_repo.db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == current_user.id, ChatParticipant.is_active == True
    ).first()
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник чата")
    new_message = message_repo.create(chat_id, current_user.id, message.content, message.type, message.attachment_id)
    manager.broadcast(json.dumps({"type": "new_message", "message": new_message.__dict__}), chat_id)
    return new_message

@app.get("/chats/{chat_id}/messages", response_model=List[MessageOut])
def get_messages(
    chat_id: int, 
    limit: int = Query(50, ge=1, le=100), 
    offset: int = Query(0, ge=0), 
    current_user: User = Depends(get_current_user), 
    message_repo: MessageRepository = Depends(get_message_repo)
):
    # проверка участия
    participant = message_repo.db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == current_user.id, ChatParticipant.is_active == True
    ).first()
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник чата")
    messages = message_repo.get_by_chat(chat_id, limit, offset)
    return messages

# поиск по сообщениям
@app.get("/chats/{chat_id}/messages/search", response_model=List[MessageOut])
def search_messages(
    chat_id: int, 
    q: str = Query(..., min_length=1), 
    limit: int = Query(50, ge=1, le=100), 
    offset: int = Query(0, ge=0), 
    current_user: User = Depends(get_current_user), 
    message_repo: MessageRepository = Depends(get_message_repo)
):
    # проверка участия
    participant = message_repo.db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == current_user.id, ChatParticipant.is_active == True
    ).first()
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник чата")
    messages = message_repo.search_by_chat(chat_id, q, limit, offset)
    return messages

# редактирование сообщений
@app.patch("/chats/{chat_id}/messages/{message_id}", response_model=MessageOut)
def update_message(chat_id: int, message_id: int, update_data: MessageUpdate, current_user: User = Depends(get_current_user), message_repo: MessageRepository = Depends(get_message_repo)):
    # проверка, что сообщение в чате и принадлежит пользователю
    message = message_repo.get_by_id(message_id)
    if not message or message.chat_id != chat_id or message.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Сообщение не найдено или недоступно")
    updated_message = message_repo.update(message_id, update_data.content, current_user.id)
    if not updated_message:
        raise HTTPException(status_code=400, detail="Не удалось обновить сообщение")
    return updated_message

# WebSocket
@app.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    participant = db.query(ChatParticipant).filter(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == current_user.id, ChatParticipant.is_active == True).first()
    if not participant:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await manager.connect(websocket, chat_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"User {current_user.nickname}: {data}", chat_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_id)

# создание таблиц с индексами
Base.metadata.create_all(bind=engine)