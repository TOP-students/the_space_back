import logging
from datetime import datetime, timezone
from sqlalchemy import select, or_
from jose import JWTError, jwt

from models import User, ChatParticipant, Message, Ban, Chat, Space
from utils import AsyncSessionLocal, SECRET_KEY, ALGORITHM

logger = logging.getLogger(__name__)

# Хранилище активных подключений в памяти
active_users: dict[int, str] = {}  # {user_id: sid}
user_rooms: dict[int, set[int]] = {}  # {user_id: {chat_ids}}


def register_socketio_handlers(sio):
    """Регистрация всех обработчиков Socket.IO событий."""

    @sio.event
    async def connect(sid, environ, auth):
        """Обработка подключения клиента с JWT аутентификацией."""
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
        except (JWTError, ValueError, TypeError):
            await sio.disconnect(sid)
            return

        active_users[user_id] = sid
        user_rooms[user_id] = set()

        # Обновляем статус пользователя в БД
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(User).filter(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                if user:
                    user.status = "online"
                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to update user status: {e}")

        logger.info(f"User {user_id} connected (SID={sid})")

        await sio.emit("user_status_changed", {
            "user_id": user_id,
            "status": "online",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    @sio.event
    async def disconnect(sid):
        """Обработка отключения клиента."""
        user_id = next(
            (uid for uid, s in active_users.items() if s == sid),
            None
        )
        if not user_id:
            return

        del active_users[user_id]
        user_rooms.pop(user_id, None)

        # Обновляем статус в БД
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(User).filter(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                if user:
                    user.status = "offline"
                    await session.commit()
        except Exception as e:
            logger.error(f"Failed to update user status: {e}")

        logger.info(f"User {user_id} disconnected")

        await sio.emit("user_status_changed", {
            "user_id": user_id,
            "status": "offline",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    @sio.on("join_room")
    async def handle_join_room(sid, data):
        """Обработка присоединения пользователя к комнате чата."""
        # Валидируем входные данные
        if not isinstance(data, dict):
            await sio.emit("error", {"message": "Invalid data"}, to=sid)
            return

        chat_id = data.get("chat_id")
        if not chat_id or not isinstance(chat_id, int):
            await sio.emit(
                "error",
                {"message": "chat_id обязателен"},
                to=sid
            )
            return

        user_id = next(
            (uid for uid, s in active_users.items() if s == sid),
            None
        )
        if not user_id:
            return

        try:
            async with AsyncSessionLocal() as session:
                # Проверяем, не забанен ли пользователь в пространстве
                chat_result = await session.execute(
                    select(Chat).filter(Chat.id == chat_id)
                )
                chat = chat_result.scalar_one_or_none()

                if chat and chat.space_id:
                    # Ищем активный бан в этом пространстве
                    ban_query = select(Ban).filter(
                        Ban.user_id == user_id,
                        Ban.space_id == chat.space_id,
                        or_(
                            Ban.until > datetime.now(timezone.utc),
                            Ban.until.is_(None)
                        )
                    )
                    ban_result = await session.execute(ban_query)
                    active_ban = ban_result.scalar_one_or_none()

                    if active_ban:
                        await sio.emit(
                            "error",
                            {"message": "Вы забанены в этом пространстве"},
                            to=sid
                        )
                        return

                # Обновляем или создаем запись участника
                result = await session.execute(
                    select(ChatParticipant).filter(
                        ChatParticipant.chat_id == chat_id,
                        ChatParticipant.user_id == user_id
                    )
                )
                existing = result.scalar_one_or_none()

                if existing and existing.is_active:
                    pass  # Уже активен
                elif existing:
                    existing.is_active = True
                else:
                    new_participant = ChatParticipant(
                        chat_id=chat_id,
                        user_id=user_id,
                        is_active=True
                    )
                    session.add(new_participant)

                await session.commit()

        except Exception as e:
            logger.error(f"Error in join_room: {e}")
            await sio.emit(
                "error",
                {"message": "Ошибка при входе в комнату"},
                to=sid
            )
            return

        room = f"chat_{chat_id}"
        await sio.enter_room(sid, room)
        user_rooms[user_id].add(chat_id)

        logger.info(f"User {user_id} joined room {chat_id}")

        await sio.emit("user_joined", {
            "chat_id": chat_id,
            "user_id": user_id
        }, room=room)

    @sio.on("leave_room")
    async def handle_leave_room(sid, data):
        """Обработка выхода пользователя из комнаты чата."""
        if not isinstance(data, dict):
            return

        chat_id = data.get("chat_id")
        if not chat_id:
            return

        user_id = next(
            (uid for uid, s in active_users.items() if s == sid),
            None
        )
        if not user_id:
            return

        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ChatParticipant).filter(
                        ChatParticipant.chat_id == chat_id,
                        ChatParticipant.user_id == user_id
                    )
                )
                participant = result.scalar_one_or_none()
                if participant:
                    participant.is_active = False
                    await session.commit()
        except Exception as e:
            logger.error(f"Error in leave_room: {e}")

        await sio.leave_room(sid, f"chat_{chat_id}")
        user_rooms[user_id].discard(chat_id)

        await sio.emit("user_left", {
            "chat_id": chat_id,
            "user_id": user_id
        }, room=f"chat_{chat_id}")

    @sio.on("send_message")
    async def handle_send_message(sid, data):
        """Обработка отправки сообщения в чат."""
        user_id = next(
            (uid for uid, s in active_users.items() if s == sid),
            None
        )
        if not user_id:
            return

        # Валидируем входные данные
        if not isinstance(data, dict):
            await sio.emit("error", {"message": "Invalid data"}, to=sid)
            return

        chat_id = data.get("chat_id")
        content = data.get("content")
        msg_type = data.get("type", "text")

        if not chat_id or not content:
            await sio.emit(
                "error",
                {"message": "chat_id и content обязательны"},
                to=sid
            )
            return

        # Проверяем длину контента
        if not isinstance(content, str) or len(content) > 5000:
            await sio.emit(
                "error",
                {"message": "Контент должен быть строкой до 5000 символов"},
                to=sid
            )
            return

        try:
            async with AsyncSessionLocal() as session:
                # Проверяем, активный ли участник
                result = await session.execute(
                    select(ChatParticipant).filter(
                        ChatParticipant.chat_id == chat_id,
                        ChatParticipant.user_id == user_id,
                        ChatParticipant.is_active.is_(True)
                    )
                )
                participant = result.scalar_one_or_none()

                if not participant:
                    await sio.emit(
                        "error",
                        {"message": "Вы не участник чата"},
                        to=sid
                    )
                    return

                # Create message
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

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            await sio.emit(
                "error",
                {"message": "Ошибка отправки сообщения"},
                to=sid
            )
