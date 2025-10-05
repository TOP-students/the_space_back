from fastapi import FastAPI
import socketio
from fastapi.middleware.cors import CORSMiddleware
from utils.websocket_manager import WebSocketManager
from utils.message_handler import MessageHandler
from utils.auth_middleware import AuthMiddleware
from datetime import datetime
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    async_mode='asgi'
)

ws_manager = WebSocketManager(sio)
message_handler = MessageHandler()
auth_middleware = AuthMiddleware()

socket_app = socketio.ASGIApp(sio, app)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/online-users")
async def get_online_users():
    """API endpoint для получения списка онлайн пользователей"""
    return {
        "online_users": list(ws_manager.user_data.keys()),
        "total_online": len(ws_manager.user_data),
        "users_info": ws_manager.user_data
    }


@app.get("/api/room-users/{room_id}")
async def get_room_users_api(room_id: str):
    """API endpoint для получения пользователей в комнате"""
    users_in_room = ws_manager.get_room_users(room_id)
    users_info = ws_manager.get_users_info(users_in_room)

    return {
        "room_id": room_id,
        "users": users_in_room,
        "users_info": users_info,
        "total_users": len(users_in_room)
    }


@sio.event
async def connect(sid, environ, auth):
    print(f"🟢 Клиент {sid} подключился")

    ws_manager.user_data[sid] = {
        "name": "Anonymous User",
        "role": "user",
        "last_seen": datetime.now().isoformat(),
        "status": "online"
    }

    await sio.emit('connected', {
        'message': 'Подключение установлено',
        'user_id': sid,
        'timestamp': datetime.now().isoformat()
    }, room=sid)

    await sio.emit('user_online', {
        'user_id': sid,
        'user_info': ws_manager.user_data[sid],
        'timestamp': datetime.now().isoformat()
    })


@sio.event
async def disconnect(sid):
    print(f"🔴 Клиент {sid} отключился")

    ws_manager.cleanup_user(sid)

    await sio.emit('user_offline', {
        'user_id': sid,
        'timestamp': datetime.now().isoformat()
    })


@sio.event
async def join_room(sid, data):
    room_id = data.get('room_id')
    user_info = data.get('user_info', {})

    if room_id:
        sio.enter_room(sid, room_id)

        ws_manager.add_user_to_room(sid, room_id, user_info)

        if sid in ws_manager.user_data:
            ws_manager.user_data[sid].update({
                'name': user_info.get('name', 'Anonymous User'),
                'role': user_info.get('role', 'user'),
                'last_seen': datetime.now().isoformat()
            })

        print(f"👤 Пользователь {sid} присоединился к комнате {room_id}")

        room_users = ws_manager.get_room_users(room_id)
        users_info = ws_manager.get_users_info(room_users)

        await sio.emit('joined_room', {
            'room_id': room_id,
            'users': room_users,
            'users_info': users_info,
            'timestamp': datetime.now().isoformat()
        }, room=sid)

        await sio.emit('user_joined_room', {
            'user_id': sid,
            'room_id': room_id,
            'user_info': ws_manager.user_data.get(sid, {}),
            'timestamp': datetime.now().isoformat()
        }, room=room_id, skip_sid=sid)


@sio.event
async def leave_room(sid, data):
    room_id = data.get('room_id')

    if room_id:
        sio.leave_room(sid, room_id)

        ws_manager.remove_user_from_room(sid, room_id)

        print(f"👋 Пользователь {sid} покинул комнату {room_id}")

        await sio.emit('left_room', {
            'room_id': room_id,
            'timestamp': datetime.now().isoformat()
        }, room=sid)

        await sio.emit('user_left_room', {
            'user_id': sid,
            'room_id': room_id,
            'timestamp': datetime.now().isoformat()
        }, room=room_id, skip_sid=sid)


@sio.event
async def send_message(sid, data):
    message_data = {
        'user_id': sid,
        'room_id': data.get('room_id'),
        'content': data.get('content')
    }

    is_valid, error = message_handler.validate_message(message_data)
    if not is_valid:
        await sio.emit('error', {'message': error}, room=sid)
        return

    message = message_handler.create_message(
        user_id=sid,
        room_id=data['room_id'],
        content=data['content']
    )

    ws_manager.update_user_activity(sid)
    message['user_info'] = ws_manager.user_data.get(sid, {})

    print(f"💬 Сообщение от {sid} в комнату {data['room_id']}: "
          f"{data['content']}")

    await sio.emit('new_message', message, room=data['room_id'])
    await sio.emit('message_sent', message, room=sid)


@sio.event
async def send_file(sid, data):
    file_data = {
        'room_id': data.get('room_id'),
        'file_info': data.get('file_info')
    }

    is_valid, error = message_handler.validate_file(file_data)
    if not is_valid:
        await sio.emit('error', {'message': error}, room=sid)
        return

    message = message_handler.create_file_message(
        user_id=sid,
        room_id=data['room_id'],
        file_info=data['file_info']
    )

    ws_manager.update_user_activity(sid)
    message['user_info'] = ws_manager.user_data.get(sid, {})

    print(f"📁 Файл от {sid} в комнату {data['room_id']}: "
          f"{data['file_info'].get('name')}")

    await sio.emit('new_file', message, room=data['room_id'])
    await sio.emit('file_sent', message, room=sid)


@sio.event
async def get_online_users_ws(sid, data):
    await sio.emit('online_users_list', {
        'online_users': list(ws_manager.user_data.keys()),
        'users_info': ws_manager.user_data,
        'total_online': len(ws_manager.user_data),
        'timestamp': datetime.now().isoformat()
    }, room=sid)


@sio.event
async def get_room_users(sid, data):
    room_id = data.get('room_id')
    if room_id:
        users_in_room = ws_manager.get_room_users(room_id)
        users_info = ws_manager.get_users_info(users_in_room)

        await sio.emit('room_users_list', {
            'room_id': room_id,
            'users': users_in_room,
            'users_info': users_info,
            'total_users': len(users_in_room),
            'timestamp': datetime.now().isoformat()
        }, room=sid)


if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
