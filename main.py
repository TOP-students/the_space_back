from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import socketio
import os
from models.base import Base, SessionLocal, engine
from routers import auth, spaces, messages, profile, notifications, stickers, roles, status
from crud.user import UserRepository
from crud.space import SpaceRepository
from crud.message import MessageRepository
from crud.role import RoleRepository
from crud.ban import BanRepository

app = FastAPI()

# CORS для продакшена
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # локальная разработка
        "https://your-frontend.onrender.com"  # фронтенд на Render
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# для проверки что сервер работает
@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "The Space API v1.0",
        "docs": "/docs"
    }

# инициализация Socket.IO сервера
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True
)

# подключение зависимостей
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

# подключение роутеров
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(spaces.router, prefix="/spaces", tags=["spaces"])
app.include_router(messages.router, prefix="/messages", tags=["messages"])
app.include_router(profile.router, prefix="/profile", tags=["profile"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
app.include_router(stickers.router, prefix="/stickers", tags=["stickers"])
app.include_router(roles.router, prefix="/spaces", tags=["roles"])
app.include_router(status.router, prefix="/status", tags=["status"])

# создание таблиц
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "The Space API is running"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# сохраняем глобальный инстанс Socket.IO
from utils.socketio_instance import set_sio
set_sio(sio)

# импорт обработчиков Socket.IO (после создания sio)
from utils.socketio_handlers import register_socketio_handlers
register_socketio_handlers(sio)

# обёртка FastAPI приложения в Socket.IO
app_with_socketio = socketio.ASGIApp(sio, app)

if __name__ == "__main__":
    uvicorn.run(app_with_socketio, host="0.0.0.0", port=8080)