from fastapi import APIRouter, Depends
from typing import Optional

from schemas.user import UserCreate, UserOut, Token
from utils.auth import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_db
from models.base import User
from crud.user import UserRepository
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import HTTPException

router = APIRouter()

@router.post("/register", response_model=UserOut)
def register(user: UserCreate, user_repo: UserRepository = Depends(lambda: UserRepository(get_db()))):
    if user_repo.get_by_nickname(user.nickname):
        raise HTTPException(status_code=400, detail="Никнейм уже занят")
    if user.email and user_repo.get_by_email(user.email):
        raise HTTPException(status_code=400, detail="Email уже используется")
    new_user = user_repo.create(user.nickname, user.email or None, user.password)
    return new_user

@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), user_repo: UserRepository = Depends(lambda: UserRepository(get_db()))):
    user = user_repo.get_by_nickname(form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный никнейм или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}