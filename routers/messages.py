from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from typing import List
import json

from schemas.message import MessageCreate, MessageOut, MessageUpdate
from utils.auth import get_current_user, get_db
from models.base import User, ChatParticipant
from crud.message import MessageRepository
from fastapi import status
from fastapi import HTTPException

router = APIRouter()

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

@router.post("/{chat_id}", response_model=MessageOut)
def send_message(chat_id: int, message: MessageCreate, current_user: User = Depends(get_current_user), message_repo: MessageRepository = Depends(lambda: MessageRepository(get_db()))):
    participant = message_repo.db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == current_user.id, ChatParticipant.is_active == True
    ).first()
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник чата")
    new_message = message_repo.create(chat_id, current_user.id, message.content, message.type, message.attachment_id)
    manager.broadcast(json.dumps({"type": "new_message", "message": new_message.__dict__}), chat_id)
    return new_message

@router.get("/{chat_id}", response_model=List[MessageOut])
def get_messages(
    chat_id: int, 
    limit: int = Query(50, ge=1, le=100), 
    offset: int = Query(0, ge=0), 
    current_user: User = Depends(get_current_user), 
    message_repo: MessageRepository = Depends(lambda: MessageRepository(get_db()))
):
    participant = message_repo.db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == current_user.id, ChatParticipant.is_active == True
    ).first()
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник чата")
    messages = message_repo.get_by_chat(chat_id, limit, offset)
    return messages

@router.get("/{chat_id}/search", response_model=List[MessageOut])
def search_messages(
    chat_id: int, 
    q: str = Query(..., min_length=1), 
    limit: int = Query(50, ge=1, le=100), 
    offset: int = Query(0, ge=0), 
    current_user: User = Depends(get_current_user), 
    message_repo: MessageRepository = Depends(lambda: MessageRepository(get_db()))
):
    participant = message_repo.db.query(ChatParticipant).filter(
        ChatParticipant.chat_id == chat_id, ChatParticipant.user_id == current_user.id, ChatParticipant.is_active == True
    ).first()
    if not participant:
        raise HTTPException(status_code=403, detail="Вы не участник чата")
    messages = message_repo.search_by_chat(chat_id, q, limit, offset)
    return messages

@router.patch("/{chat_id}/{message_id}", response_model=MessageOut)
def update_message(chat_id: int, message_id: int, update_data: MessageUpdate, current_user: User = Depends(get_current_user), message_repo: MessageRepository = Depends(lambda: MessageRepository(get_db()))):
    message = message_repo.get_by_id(message_id)
    if not message or message.chat_id != chat_id or message.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Сообщение не найдено или недоступно")
    updated_message = message_repo.update(message_id, update_data.content, current_user.id)
    if not updated_message:
        raise HTTPException(status_code=400, detail="Не удалось обновить сообщение")
    return updated_message

@router.websocket("/{chat_id}")
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