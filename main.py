import logging
import socketio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from models import Base
from utils import engine
from routers import auth, chats, spaces, roles
from websockets import register_socketio_handlers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    """Менеджер жизненного цикла приложения (запуск/остановка)."""
    # Запуск - создаем таблицы БД
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")
    yield
    # Остановка (если понадобится в будущем)


# Инициализация FastAPI приложения
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Chat App API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Инициализация Socket.IO сервера
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*"
)

# Оборачиваем FastAPI в ASGI приложение с Socket.IO
socket_app = socketio.ASGIApp(sio, app)

# Регистрация обработчиков Socket.IO событий
register_socketio_handlers(sio)

# Подключение API роутеров
app.include_router(auth.router)
app.include_router(chats.router)
app.include_router(spaces.router)
app.include_router(roles.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        socket_app,
        host="0.0.0.0",
        port=8000,
        ws="none"  # Отключаем websockets uvicorn, Socket.IO сам их обрабатывает
    )
