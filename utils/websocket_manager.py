import socketio
from typing import Dict, List
from datetime import datetime


class WebSocketManager:

    def __init__(self, sio: socketio.AsyncServer):
        self.sio = sio
        self.rooms: Dict[str, List[str]] = {}
        self.user_rooms: Dict[str, List[str]] = {}
        self.user_data: Dict[str, Dict] = {}

    def add_user_to_room(self, user_id: str, room_id: str, user_info: Dict = None):
        if room_id not in self.rooms:
            self.rooms[room_id] = []

        if user_id not in self.rooms[room_id]:
            self.rooms[room_id].append(user_id)

        if user_id not in self.user_rooms:
            self.user_rooms[user_id] = []

        if room_id not in self.user_rooms[user_id]:
            self.user_rooms[user_id].append(room_id)

        if user_info:
            self.user_data[user_id] = user_info

    def remove_user_from_room(self, user_id: str, room_id: str):
        if room_id in self.rooms and user_id in self.rooms[room_id]:
            self.rooms[room_id].remove(user_id)

        if user_id in self.user_rooms and room_id in self.user_rooms[user_id]:
            self.user_rooms[user_id].remove(room_id)

    def get_room_users(self, room_id: str) -> List[str]:
        return self.rooms.get(room_id, [])

    def get_user_rooms(self, user_id: str) -> List[str]:
        return self.user_rooms.get(user_id, [])

    def cleanup_user(self, user_id: str):
        if user_id in self.user_rooms:
            for room_id in self.user_rooms[user_id]:
                if room_id in self.rooms and user_id in self.rooms[room_id]:
                    self.rooms[room_id].remove(user_id)
            del self.user_rooms[user_id]

        if user_id in self.user_data:
            del self.user_data[user_id]

    def update_user_activity(self, user_id: str):
        if user_id in self.user_data:
            self.user_data[user_id]['last_seen'] = datetime.now().isoformat()

    def get_users_info(self, user_ids: List[str]) -> Dict[str, Dict]:
        return {user_id: self.user_data.get(user_id, {}) for user_id in user_ids}
