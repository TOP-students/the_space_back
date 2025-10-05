from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger, Text, JSON
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

# настройки
SECRET_KEY = ""
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# коннект с PostgreSQL
DATABASE_URL = ""
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# хэширование паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="Chat App API")

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
    user1_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user2_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

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
    permissions = Column(JSON)  # JSON для списка прав, типа ["kick", "ban"]
    color = Column(String(7))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Space(Base):
    __tablename__ = "spaces"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    admin_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    background_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ChatParticipant(Base):
    __tablename__ = "chat_participants"
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

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
    content: str
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

# зависимости
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

# функция проверки прав
def check_permissions(db, user_id: int, space_id: int, required_permission: str) -> bool:
    user_role = db.query(UserRole).join(Role).filter(
        UserRole.user_id == user_id, Role.space_id == space_id
    ).first()
    if not user_role:
        return False
    permissions = user_role.role.permissions or []
    if isinstance(permissions, str):
        permissions = json.loads(permissions)
    return required_permission in permissions or "admin" in permissions  # админ имеет все права

# утилиты (хэширование и JWT)
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

# WebSocket менеджер для чатов
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

# эндпоинты

# регистрация (проверка email)
@app.post("/register", response_model=UserOut)
def register(user: UserCreate, db=Depends(get_db)):
    if db.query(User).filter(User.nickname == user.nickname).first():
        raise HTTPException(status_code=400, detail="Никнейм уже занят")
    if user.email and db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email уже используется")
    hashed_password = get_password_hash(user.password)
    new_user = User(nickname=user.nickname, email=user.email, password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# вход
@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    user = db.query(User).filter(User.nickname == form_data.username).first()
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

# создание пространства (автоматическое создание чата, добавление админа как участника)
@app.post("/spaces", response_model=SpaceOut)
def create_space(space: SpaceCreate, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    new_space = Space(name=space.name, description=space.description, admin_id=current_user.id, background_url=space.background_url)
    db.add(new_space)
    db.commit()
    db.refresh(new_space)
    
    # создаём чат для пространства
    chat = Chat(type="group", user1_id=new_space.id, user2_id=current_user.id)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    
    # добавляем админа как участника чата
    participant = ChatParticipant(chat_id=chat.id, user_id=current_user.id, is_active=True)
    db.add(participant)
    db.commit()
    
    new_space.chat_id = chat.id
    return new_space

# вход в пространство (добавление в chat_participants, проверка бана)
@app.post("/spaces/{space_id}/join")
def join_space(space_id: int, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    space = db.query(Space).filter(Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")
    
    # проверка бана
    active_ban = db.query(Ban).filter(
        Ban.user_id == current_user.id, 
        Ban.space_id == space_id,
        Ban.until > datetime.now(timezone.utc) | Ban.until.is_(None)
    ).first()
    if active_ban:
        raise HTTPException(status_code=403, detail="Вы забанены в этом пространстве")
    
    # получаем чат пространства
    chat = db.query(Chat).filter(Chat.user1_id == space_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат для пространства не найден")
    
    # проверяем, не участник ли уже
    existing = db.query(ChatParticipant).filter(ChatParticipant.chat_id == chat.id, ChatParticipant.user_id == current_user.id).first()
    if existing and existing.is_active:
        raise HTTPException(status_code=400, detail="Вы уже участник")
    
    if existing:
        existing.is_active = True
    else:
        new_participant = ChatParticipant(chat_id=chat.id, user_id=current_user.id, is_active=True)
        db.add(new_participant)
    
    db.commit()
    return {"message": "Успешно присоединены к пространству"}

# получение списка участников пространства (через chat_participants + роли)
@app.get("/spaces/{space_id}/participants", response_model=List[UserOut])
def get_participants(space_id: int, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    space = db.query(Space).filter(Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")
    
    chat = db.query(Chat).filter(Chat.user1_id == space_id).first()
    if not chat:
        return []
    
    participants = db.query(User).join(ChatParticipant).filter(ChatParticipant.chat_id == chat.id, ChatParticipant.is_active == True).all()
    return participants

# кик (проверка прав для кика)
@app.delete("/spaces/{space_id}/kick/{user_id}")
def kick_user(space_id: int, user_id: int, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    if not check_permissions(db, current_user.id, space_id, "kick"):
        raise HTTPException(status_code=403, detail="У вас нет прав на кик")
    
    space = db.query(Space).filter(Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")
    
    chat = db.query(Chat).filter(Chat.user1_id == space_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    participant = db.query(ChatParticipant).filter(ChatParticipant.chat_id == chat.id, ChatParticipant.user_id == user_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Пользователь не найден в пространстве")
    
    participant.is_active = False
    db.commit()
    return {"message": "Пользователь успешно кикнут"}

# бан (проверка прав для бана)
@app.post("/spaces/{space_id}/ban/{user_id}")
def ban_user(space_id: int, user_id: int, ban_data: BanCreate, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    if not check_permissions(db, current_user.id, space_id, "ban"):
        raise HTTPException(status_code=403, detail="У вас нет прав на бан")
    
    space = db.query(Space).filter(Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")
    
    new_ban = Ban(user_id=user_id, banned_by=current_user.id, space_id=space_id, reason=ban_data.reason, until=ban_data.until)
    db.add(new_ban)
    
    # деактивируем участие
    chat = db.query(Chat).filter(Chat.user1_id == space_id).first()
    if chat:
        participant = db.query(ChatParticipant).filter(ChatParticipant.chat_id == chat.id, ChatParticipant.user_id == user_id).first()
        if participant:
            participant.is_active = False
    
    db.commit()
    return {"message": "Пользователь успешно забанен"}

# назначение роли (проверка прав, permissions как список)
@app.post("/spaces/{space_id}/assign-role/{user_id}/{role_id}")
def assign_role(space_id: int, user_id: int, role_id: int, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    if not check_permissions(db, current_user.id, space_id, "assign_role"):
        raise HTTPException(status_code=403, detail="У вас нет прав на назначение ролей")
    
    space = db.query(Space).filter(Space.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")
    
    role = db.query(Role).filter(Role.id == role_id, Role.space_id == space_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Роль не найдена")
    
    existing = db.query(UserRole).filter(UserRole.user_id == user_id, UserRole.role_id == role_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Роль уже назначена")
    
    new_user_role = UserRole(user_id=user_id, role_id=role_id)
    db.add(new_user_role)
    db.commit()
    return {"message": "Роль успешно назначена"}

# ++ отправка сообщения
@app.post("/chats/{chat_id}/messages", response_model=MessageOut)
def send_message(chat_id: int, message: MessageCreate, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    # проверка участия
    participant = db.query(ChatParticipant).filter(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == current_user.id, ChatParticipant.is_active == True).first()
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник чата")
    
    new_message = Message(chat_id=chat_id, user_id=current_user.id, content=message.content, type=message.type, attachment_id=message.attachment_id)
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    # уведомление через WebSocket
    manager.broadcast(json.dumps({"type": "new_message", "message": new_message.__dict__}), chat_id)
    
    return new_message

# ++ получение сообщений
@app.get("/chats/{chat_id}/messages", response_model=List[MessageOut])
def get_messages(chat_id: int, limit: int = 50, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    participant = db.query(ChatParticipant).filter(ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == current_user.id, ChatParticipant.is_active == True).first()
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник чата")
    
    messages = db.query(Message).filter(Message.chat_id == chat_id, Message.is_deleted == False).order_by(Message.created_at.desc()).limit(limit).all()
    return messages[::-1]  # Реверс для хронологического порядка

# ++ WebSocket для чата
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
            # можно обработать входящие сообщения, для простоты просто broadcast
            await manager.broadcast(f"User {current_user.nickname}: {data}", chat_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_id)

# создание таблиц
Base.metadata.create_all(bind=engine)