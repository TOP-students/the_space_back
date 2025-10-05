from typing import Dict, Any, Tuple
import uuid
from datetime import datetime


class MessageHandler:
    """Обработчик сообщений и файлов"""

    MAX_MESSAGE_LENGTH = 2000
    MAX_FILE_SIZE = 50 * 1024 * 1024

    @staticmethod
    def create_message(user_id: str, room_id: str, content: str,
                      message_type: str = "text") -> Dict[str, Any]:
        return {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'room_id': room_id,
            'content': content,
            'type': message_type,
            'timestamp': datetime.now().isoformat(),
            'edited': False,
            'deleted': False
        }
    
    @staticmethod
    def create_file_message(user_id: str, room_id: str, 
                           file_info: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'room_id': room_id,
            'content': file_info.get('name', 'file'),
            'type': 'file',
            'file_info': file_info,
            'timestamp': datetime.now().isoformat(),
            'edited': False,
            'deleted': False
        }

    @staticmethod
    def validate_message(data: Dict[str, Any]) -> Tuple[bool, str]:
        if not data.get('content'):
            return False, "Содержимое сообщения не может быть пустым"

        if not data.get('room_id'):
            return False, "ID комнаты обязателен"

        if not data.get('user_id'):
            return False, "ID пользователя обязателен"

        if len(data['content']) > MessageHandler.MAX_MESSAGE_LENGTH:
            return False, f"Сообщение слишком длинное (максимум {MessageHandler.MAX_MESSAGE_LENGTH} символов)"

        return True, ""

    @staticmethod
    def validate_file(data: Dict[str, Any]) -> Tuple[bool, str]:
        """Валидация файла"""
        file_info = data.get('file_info', {})

        if not file_info.get('name'):
            return False, "Имя файла обязательно"

        if not file_info.get('url'):
            return False, "URL файла обязателен"

        if file_info.get('size', 0) > MessageHandler.MAX_FILE_SIZE:
            return False, f"Файл слишком большой (максимум {MessageHandler.MAX_FILE_SIZE // (1024*1024)}MB)"

        return True, ""
