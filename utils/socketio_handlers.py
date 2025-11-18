import socketio
from typing import Dict
from models.base import SessionLocal, ChatParticipant, User
from crud.message import MessageRepository
from crud.ban import BanRepository
from utils.websocket_manager import WebSocketManager


# Хранилище для связи sid -> user_info
user_sessions: Dict[str, Dict] = {}

# Менеджер WebSocket соединений
ws_manager = None


def register_socketio_handlers(sio: socketio.AsyncServer):
    """Регистрация всех обработчиков Socket.IO событий"""

    global ws_manager
    ws_manager = WebSocketManager(sio)

    @sio.event
    async def connect(sid, environ, auth):
        """Подключение клиента к Socket.IO"""
        try:
            # Извлекаем параметры из query string
            query_string = environ.get('QUERY_STRING', '')
            params = dict(param.split('=') for param in query_string.split('&') if '=' in param)

            user_id = params.get('user_id')
            nickname = params.get('nickname', 'Unknown')

            if not user_id:
                print(f"[Socket.IO] Connection rejected: no user_id")
                return False

            # Сохраняем информацию о сессии
            user_sessions[sid] = {
                'user_id': user_id,
                'nickname': nickname,
                'sid': sid
            }

            try:
                print(f"[Socket.IO] User {nickname} (ID: {user_id}) connected with sid: {sid}")
            except UnicodeEncodeError:
                print(f"[Socket.IO] User [Unicode name] (ID: {user_id}) connected with sid: {sid}")

            # Отправляем подтверждение подключения
            await sio.emit('connected', {
                'message': 'Successfully connected to Socket.IO server',
                'user_id': user_id,
                'nickname': nickname
            }, room=sid)

            return True

        except Exception as e:
            print(f"[Socket.IO] Connect error: {e}")
            return False


    @sio.event
    async def disconnect(sid):
        """Отключение клиента"""
        try:
            user_info = user_sessions.get(sid)
            if user_info:
                user_id = user_info['user_id']
                nickname = user_info['nickname']

                # Очищаем из всех комнат
                if ws_manager:
                    rooms = ws_manager.get_user_rooms(user_id)
                    for room_id in rooms:
                        ws_manager.remove_user_from_room(user_id, room_id)
                        await sio.emit('user_left_room', {
                            'user_id': user_id,
                            'nickname': nickname,
                            'room_id': room_id
                        }, room=room_id, skip_sid=sid)

                # Удаляем из сессий
                del user_sessions[sid]

                try:
                    print(f"[Socket.IO] User {nickname} (ID: {user_id}) disconnected")
                except UnicodeEncodeError:
                    print(f"[Socket.IO] User [Unicode name] (ID: {user_id}) disconnected")
        except Exception as e:
            print(f"[Socket.IO] Disconnect error: {e}")


    @sio.event
    async def join_room(sid, data):
        """Присоединение к комнате"""
        try:
            room_id = str(data.get('room_id'))
            user_id = str(data.get('user_id'))
            nickname = data.get('nickname', 'Unknown')

            if not room_id or not user_id:
                await sio.emit('error', {'message': 'room_id and user_id are required'}, room=sid)
                return

            # Проверка прав доступа через БД
            db = SessionLocal()
            try:
                # Проверяем, является ли пользователь участником чата
                participant = db.query(ChatParticipant).filter(
                    ChatParticipant.chat_id == int(room_id),
                    ChatParticipant.user_id == int(user_id),
                    ChatParticipant.is_active == True
                ).first()

                if not participant:
                    await sio.emit('error', {'message': 'Access denied: not a participant'}, room=sid)
                    return

                # Проверяем бан
                ban_repo = BanRepository(db)
                # Получаем space_id через чат
                from models.base import Chat
                chat = db.query(Chat).filter(Chat.id == int(room_id)).first()
                if chat and chat.space_id:
                    if ban_repo.is_active(int(user_id), chat.space_id):
                        await sio.emit('error', {'message': 'You are banned from this space'}, room=sid)
                        return

            finally:
                db.close()

            # Добавляем в Socket.IO room
            await sio.enter_room(sid, room_id)

            # Добавляем в WebSocketManager
            if ws_manager:
                ws_manager.add_user_to_room(user_id, room_id, {
                    'nickname': nickname,
                    'sid': sid
                })

            try:
                print(f"[Socket.IO] User {nickname} joined room {room_id}")
            except UnicodeEncodeError:
                print(f"[Socket.IO] User [Unicode name] joined room {room_id}")

            # Уведомляем пользователя
            await sio.emit('joined_room', {
                'room_id': room_id,
                'message': f'You joined room {room_id}'
            }, room=sid)

            # Уведомляем остальных участников
            await sio.emit('user_joined_room', {
                'user_id': user_id,
                'nickname': nickname,
                'room_id': room_id
            }, room=room_id, skip_sid=sid)

        except Exception as e:
            try:
                print(f"[Socket.IO] Join room error: {e}")
            except UnicodeEncodeError:
                print(f"[Socket.IO] Join room error: [Unicode error]")
            await sio.emit('error', {'message': f'Failed to join room: {str(e)}'}, room=sid)


    @sio.event
    async def leave_room(sid, data):
        """Покинуть комнату"""
        try:
            room_id = str(data.get('room_id'))
            user_id = str(data.get('user_id'))

            user_info = user_sessions.get(sid, {})
            nickname = user_info.get('nickname', 'Unknown')

            if not room_id or not user_id:
                await sio.emit('error', {'message': 'room_id and user_id are required'}, room=sid)
                return

            # Удаляем из Socket.IO room
            await sio.leave_room(sid, room_id)

            # Удаляем из WebSocketManager
            if ws_manager:
                ws_manager.remove_user_from_room(user_id, room_id)

            try:
                print(f"[Socket.IO] User {nickname} left room {room_id}")
            except UnicodeEncodeError:
                print(f"[Socket.IO] User [Unicode name] left room {room_id}")

            # Уведомляем пользователя
            await sio.emit('left_room', {
                'room_id': room_id,
                'message': f'You left room {room_id}'
            }, room=sid)

            # Уведомляем остальных участников
            await sio.emit('user_left_room', {
                'user_id': user_id,
                'nickname': nickname,
                'room_id': room_id
            }, room=room_id)

        except Exception as e:
            try:
                print(f"[Socket.IO] Leave room error: {e}")
            except UnicodeEncodeError:
                print(f"[Socket.IO] Leave room error: [Unicode error]")
            await sio.emit('error', {'message': f'Failed to leave room: {str(e)}'}, room=sid)


    @sio.event
    async def send_message(sid, data):
        """Отправка сообщения в комнату"""
        try:
            room_id = str(data.get('room_id'))
            user_id = data.get('user_id')
            nickname = data.get('nickname', 'Unknown')
            message_content = data.get('message')

            if not room_id or not user_id or not message_content:
                await sio.emit('error', {'message': 'room_id, user_id and message are required'}, room=sid)
                return

            # Сохраняем сообщение в БД
            db = SessionLocal()
            try:
                message_repo = MessageRepository(db)

                # Получаем информацию о пользователе
                user = db.query(User).filter(User.id == int(user_id)).first()
                if not user:
                    await sio.emit('error', {'message': 'User not found'}, room=sid)
                    return

                # Создаём сообщение
                new_message = message_repo.create(
                    chat_id=int(room_id),
                    user_id=int(user_id),
                    content=message_content,
                    type='text'
                )

                # Формируем данные для отправки
                message_data = {
                    'id': new_message.id,
                    'chat_id': new_message.chat_id,
                    'room_id': room_id,
                    'user_id': new_message.user_id,
                    'content': new_message.content,
                    'message': new_message.content,  # для совместимости
                    'type': new_message.type,
                    'created_at': new_message.created_at.isoformat(),
                    'timestamp': new_message.created_at.isoformat(),
                    'user_nickname': user.nickname,
                    'nickname': user.nickname,  # для совместимости
                    'user_avatar_url': user.avatar_url  # добавляем аватар
                }

                try:
                    print(f"[Socket.IO] Message from {nickname} in room {room_id}: {message_content}")
                except UnicodeEncodeError:
                    print(f"[Socket.IO] Message from user in room {room_id} [contains Unicode]")

                # Подтверждаем отправителю
                await sio.emit('message_sent', message_data, room=sid)

                # Broadcast всем в комнате
                await sio.emit('new_message', message_data, room=room_id)

            finally:
                db.close()

        except Exception as e:
            try:
                print(f"[Socket.IO] Send message error: {e}")
            except UnicodeEncodeError:
                print(f"[Socket.IO] Send message error: [Unicode error]")
            await sio.emit('error', {'message': f'Failed to send message: {str(e)}'}, room=sid)


    @sio.event
    async def get_room_users(sid, data):
        """Получить список пользователей в комнате"""
        try:
            room_id = str(data.get('room_id'))

            if not room_id:
                await sio.emit('error', {'message': 'room_id is required'}, room=sid)
                return

            if ws_manager:
                user_ids = ws_manager.get_room_users(room_id)
                users_info = ws_manager.get_users_info(user_ids)

                await sio.emit('room_users', {
                    'room_id': room_id,
                    'users': users_info
                }, room=sid)
            else:
                await sio.emit('room_users', {
                    'room_id': room_id,
                    'users': {}
                }, room=sid)

        except Exception as e:
            try:
                print(f"[Socket.IO] Get room users error: {e}")
            except UnicodeEncodeError:
                print(f"[Socket.IO] Get room users error: [Unicode error]")
            await sio.emit('error', {'message': f'Failed to get room users: {str(e)}'}, room=sid)


    @sio.event
    async def edit_message(sid, data):
        """Редактирование сообщения"""
        try:
            room_id = str(data.get('room_id'))
            message_id = data.get('message_id')
            content = data.get('content')
            user_id = data.get('user_id')

            print(f"[Socket.IO] RECEIVED edit_message event from sid {sid}")
            print(f"[Socket.IO] Data: room_id={room_id}, message_id={message_id}, user_id={user_id}")

            if not room_id or not message_id or not content or not user_id:
                await sio.emit('error', {'message': 'room_id, message_id, content and user_id are required'}, room=sid)
                return

            # Получаем список всех участников комнаты
            try:
                room_sids = sio.manager.rooms.get(room_id, set())
                print(f"[Socket.IO] Room {room_id} has {len(room_sids)} participants: {room_sids}")
            except Exception as e:
                print(f"[Socket.IO] Could not get room participants: {e}")
            print(f"[Socket.IO] Broadcasting to room {room_id}, skipping sid {sid}")

            # Broadcast обновление сообщения всем в комнате
            # ВРЕМЕННО БЕЗ skip_sid для отладки
            await sio.emit('message_edited', {
                'room_id': room_id,
                'message_id': message_id,
                'content': content,
                'user_id': user_id
            }, room=room_id)

            print(f"[Socket.IO] Message {message_id} edited in room {room_id} - broadcast sent")

        except Exception as e:
            try:
                print(f"[Socket.IO] Edit message error: {e}")
                import traceback
                traceback.print_exc()
            except UnicodeEncodeError:
                print(f"[Socket.IO] Edit message error: [Unicode error]")
            await sio.emit('error', {'message': f'Failed to edit message: {str(e)}'}, room=sid)


    @sio.event
    async def delete_message(sid, data):
        """Удаление сообщения"""
        try:
            room_id = str(data.get('room_id'))
            message_id = data.get('message_id')
            user_id = data.get('user_id')

            print(f"[Socket.IO] RECEIVED delete_message event from sid {sid}")
            print(f"[Socket.IO] Data: room_id={room_id}, message_id={message_id}, user_id={user_id}")

            if not room_id or not message_id or not user_id:
                await sio.emit('error', {'message': 'room_id, message_id and user_id are required'}, room=sid)
                return

            # Получаем список всех участников комнаты
            try:
                room_sids = sio.manager.rooms.get(room_id, set())
                print(f"[Socket.IO] Room {room_id} has {len(room_sids)} participants: {room_sids}")
            except Exception as e:
                print(f"[Socket.IO] Could not get room participants: {e}")
            print(f"[Socket.IO] Broadcasting to room {room_id}, skipping sid {sid}")

            # Broadcast удаление сообщения всем в комнате
            # ВРЕМЕННО БЕЗ skip_sid для отладки
            await sio.emit('message_deleted', {
                'room_id': room_id,
                'message_id': message_id,
                'user_id': user_id
            }, room=room_id)

            print(f"[Socket.IO] Message {message_id} deleted in room {room_id} - broadcast sent")

        except Exception as e:
            try:
                print(f"[Socket.IO] Delete message error: {e}")
                import traceback
                traceback.print_exc()
            except UnicodeEncodeError:
                print(f"[Socket.IO] Delete message error: [Unicode error]")
            await sio.emit('error', {'message': f'Failed to delete message: {str(e)}'}, room=sid)


    print("[Socket.IO] Handlers registered successfully")
