import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import timedelta

from models import User
from schemas import UserCreate, UserOut, Token
from utils import (
    get_async_db,
    verify_password,
    get_password_hash,
    create_access_token,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=UserOut)
async def register(
    user: UserCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """Регистрация нового пользователя."""
    try:
        # Проверяем, не занят ли никнейм
        result = await db.execute(
            select(User).filter(User.nickname == user.nickname)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Никнейм уже занят"
            )

        # Проверяем, не занят ли email
        if user.email:
            result = await db.execute(
                select(User).filter(User.email == user.email)
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail="Email уже используется"
                )

        # Создаем нового пользователя
        hashed_password = get_password_hash(user.password)
        new_user = User(
            nickname=user.nickname,
            email=user.email,
            password_hash=hashed_password
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        logger.info(f"New user registered: {new_user.nickname}")
        return new_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Ошибка при регистрации"
        )


@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db)
):
    """Вход в систему и получение токена доступа."""
    try:
        result = await db.execute(
            select(User).filter(User.nickname == form_data.username)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(
            form_data.password,
            user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный никнейм или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )

        logger.info(f"User logged in: {user.nickname}")
        return {"access_token": access_token, "token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Ошибка при входе"
        )


@router.post("/logout")
async def logout(request: Request):
    """Выход из системы (истечение токена обрабатывается на клиенте)."""
    return {"message": "Успешный выход (токен истёк)"}
