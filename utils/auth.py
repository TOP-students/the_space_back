from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os
from models.base import SessionLocal, User, verify_password

load_dotenv()

# пробуем сначала python-jose, если нет - используем PyJWT
try:
    from jose import JWTError, jwt
except ImportError:
    import jwt
    JWTError = jwt.InvalidTokenError

# конфигурация JWT
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-me-in-production-12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 часа по умолчанию

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_db():
    """Dependency для получения сессии БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создание JWT токена"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # проверяем какая библиотека используется
    try:
        from jose import jwt as jose_jwt
        encoded_jwt = jose_jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    except ImportError:
        import jwt as pyjwt
        encoded_jwt = pyjwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt

async def update_user_activity_middleware(user_id: int, db: Session):
    """Обновить активность при каждом запросе"""
    from crud.activity import ActivityRepository
    activity_repo = ActivityRepository(db)
    activity_repo.update_activity(user_id, status="online")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Получение текущего пользователя из JWT токена"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось валидировать токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        try:
            from jose import jwt as jose_jwt
            payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except ImportError:
            import jwt as pyjwt
            payload = pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    
    # обновление активности
    await update_user_activity_middleware(user.id, db)
    
    return user

def check_permissions(db: Session, user_id: int, space_id: int, required_permission: str) -> bool:
    """Проверка прав доступа (упрощённая версия для прототипа)"""
    from models.base import Space
    
    # проверка на админа комнаты
    space = db.query(Space).filter(Space.id == space_id).first()
    if space and space.admin_id == user_id:
        return True
    
    # Для прототипа: все участники могут отправлять сообщения
    # Полноценную систему ролей добавим потом
    return True