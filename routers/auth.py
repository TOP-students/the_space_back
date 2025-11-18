from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from sqlalchemy.orm import Session

from schemas.user import UserCreate, UserOut, Token
from models.base import User, SessionLocal, get_password_hash, verify_password
from crud.user import UserRepository
from utils.auth import create_access_token, get_db, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user

router = APIRouter()

@router.post("/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    user_repo = UserRepository(db)
    
    # Проверка на существующий никнейм
    if user_repo.get_by_nickname(user.nickname):
        raise HTTPException(status_code=400, detail="Никнейм уже занят")
    
    # Проверка на существующий email (если указан)
    if user.email and user_repo.get_by_email(user.email):
        raise HTTPException(status_code=400, detail="Email уже используется")
    
    # Создание пользователя
    new_user = user_repo.create(user.nickname, user.email or None, user.password)
    return new_user

@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """Вход и получение JWT токена"""
    user_repo = UserRepository(db)
    user = user_repo.get_by_nickname(form_data.username)
    
    # Проверка пользователя и пароля
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный никнейм или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Создаём JWT токен
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "nickname": user.nickname},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return current_user

@router.get("/check-user")
async def check_user(
    identifier: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Проверить существование пользователя по никнейму или ID"""
    user = None

    # Проверяем, является ли identifier числом (ID)
    if identifier.isdigit():
        user = db.query(User).filter(User.id == int(identifier)).first()
    else:
        # Ищем по никнейму (точное совпадение)
        user = db.query(User).filter(User.nickname == identifier).first()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return {
        "id": user.id,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url
    }