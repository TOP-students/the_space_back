from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import socketio

from models.base import Base, SessionLocal, engine
from routers import auth, spaces, messages
from crud.user import UserRepository
from crud.space import SpaceRepository
from crud.message import MessageRepository
from crud.role import RoleRepository
from crud.ban import BanRepository

app = FastAPI()

# Инициализация Socket.IO сервера
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

# Импорт обработчиков Socket.IO (после создания sio)
from utils.socketio_handlers import register_socketio_handlers
register_socketio_handlers(sio)

# Обёртка FastAPI приложения в Socket.IO
app_with_socketio = socketio.ASGIApp(sio, app)

if __name__ == "__main__":
    uvicorn.run(app_with_socketio, host="0.0.0.0", port=8000)