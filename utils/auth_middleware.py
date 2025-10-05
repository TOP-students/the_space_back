from typing import Optional, Dict, Any
from jose import jwt
from datetime import datetime, timedelta
import os


class AuthMiddleware:

    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or os.getenv('JWT_SECRET_KEY', 'your-secret-key')
        self.algorithm = 'HS256'

    def create_token(self, user_data: Dict[str, Any], expires_delta: timedelta = None) -> str:
        """Создать JWT токен"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)

        to_encode = user_data.copy()
        to_encode.update({"exp": expire})

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None

    async def authenticate_connection(self, auth_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        token = auth_data.get('token')
        if not token:
            return None

        user_data = self.verify_token(token)
        return user_data

    def check_permission(self, user_data: Dict[str, Any], action: str, room_id: str = None) -> bool:
        user_role = user_data.get('role', 'user')

        if user_role == 'admin':
            return True

        if user_role == 'moderator' and action in ['kick_user', 'ban_user', 'manage_room']:
            return True

        if user_role == 'user' and action in ['send_message', 'send_file']:
            return True

        return False
