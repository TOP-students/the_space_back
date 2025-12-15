from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import bcrypt

from schemas.profile import ProfileUpdate, ProfileOut, MyProfileOut
from utils.auth import get_current_user, get_db
from utils.storage import upload_image_to_storage, delete_image_from_storage
from models.base import User

router = APIRouter()


@router.get("/me", response_model=MyProfileOut)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить свой профиль"""
    # Обновляем данные из БД для гарантии актуальности
    db.refresh(current_user)
    return current_user


@router.patch("/me", response_model=MyProfileOut)
async def update_my_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить свой профиль"""

    # Обновляем только переданные поля
    if profile_data.display_name is not None:
        current_user.display_name = profile_data.display_name

    if profile_data.bio is not None:
        current_user.bio = profile_data.bio

    if profile_data.avatar_url is not None:
        current_user.avatar_url = profile_data.avatar_url

    if profile_data.profile_background_url is not None:
        current_user.profile_background_url = (
            profile_data.profile_background_url
        )

    db.commit()
    db.refresh(current_user)

    return current_user


@router.get("/{user_id}", response_model=ProfileOut)
async def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить профиль пользователя по ID"""
    from crud.activity import ActivityRepository

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Пользователь не найден"
        )

    # Получаем актуальный статус из таблицы активности
    activity_repo = ActivityRepository(db)
    status_info = activity_repo.get_user_status(user_id)

    # Обновляем статус в объекте user перед возвратом
    user.status = status_info.get('status', 'offline')

    return user


@router.get("/nickname/{nickname}", response_model=ProfileOut)
async def get_user_profile_by_nickname(
    nickname: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить профиль пользователя по никнейму"""
    user = db.query(User).filter(User.nickname == nickname).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Пользователь не найден"
        )

    return user


@router.post("/upload-avatar", response_model=MyProfileOut)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Загрузить аватар пользователя

    - Принимает изображение (JPEG, PNG, WebP)
    - Оптимизирует до 400x400px
    - Загружает в Supabase Storage
    - Обновляет профиль пользователя
    """

    # Проверка типа файла
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Неподдерживаемый формат файла. Разрешены: JPEG, PNG, WebP"
        )

    # Проверка размера файла (макс 5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Файл слишком большой. Максимум 5MB"
        )

    # Удаляем старый аватар если есть
    if current_user.avatar_url:
        await delete_image_from_storage(current_user.avatar_url)

    # Загружаем новый аватар
    avatar_url = await upload_image_to_storage(
        user_id=current_user.id,
        file_bytes=contents,
        file_type="avatar",
        content_type=file.content_type
    )

    if not avatar_url:
        raise HTTPException(
            status_code=500,
            detail="Ошибка загрузки файла"
        )

    # Обновляем профиль
    current_user.avatar_url = avatar_url
    db.commit()
    db.refresh(current_user)

    print(f"✅ Avatar uploaded for user {current_user.id}: {avatar_url}")
    return current_user


@router.post("/upload-banner", response_model=MyProfileOut)
async def upload_banner(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Загрузить баннер профиля пользователя

    - Принимает изображение (JPEG, PNG, WebP)
    - Оптимизирует до 1200x400px
    - Загружает в Supabase Storage
    - Обновляет профиль пользователя
    """

    # Проверка типа файла
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Неподдерживаемый формат файла. Разрешены: JPEG, PNG, WebP"
        )

    # Проверка размера файла (макс 10MB)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Файл слишком большой. Максимум 10MB"
        )

    # Удаляем старый баннер если есть
    if current_user.profile_background_url:
        await delete_image_from_storage(current_user.profile_background_url)

    # Загружаем новый баннер
    banner_url = await upload_image_to_storage(
        user_id=current_user.id,
        file_bytes=contents,
        file_type="banner",
        content_type=file.content_type
    )

    if not banner_url:
        raise HTTPException(
            status_code=500,
            detail="Ошибка загрузки файла"
        )

    # Обновляем профиль
    current_user.profile_background_url = banner_url
    db.commit()
    db.refresh(current_user)

    print(f"✅ Banner uploaded for user {current_user.id}: {banner_url}")
    return current_user


@router.patch("/update-nickname", response_model=MyProfileOut)
async def update_nickname(
    nickname: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновить никнейм пользователя

    - nickname: новый никнейм (от 3 до 50 символов)
    """

    # Валидация никнейма
    if not nickname or len(nickname) < 3 or len(nickname) > 50:
        raise HTTPException(
            status_code=400,
            detail="Никнейм должен быть от 3 до 50 символов"
        )

    # Проверка уникальности
    existing_user = db.query(User).filter(
        User.nickname == nickname
    ).first()
    if existing_user and existing_user.id != current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Этот никнейм уже занят"
        )

    # Обновление никнейма
    current_user.nickname = nickname
    db.commit()
    db.refresh(current_user)

    return current_user


@router.patch("/update-email", response_model=MyProfileOut)
async def update_email(
    email: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновить email пользователя

    - email: новый email
    """

    # Базовая валидация email
    if not email or "@" not in email or "." not in email:
        raise HTTPException(
            status_code=400,
            detail="Некорректный email адрес"
        )

    # Проверка уникальности
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user and existing_user.id != current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Этот email уже используется"
        )

    # Обновление email
    current_user.email = email
    db.commit()
    db.refresh(current_user)

    return current_user


@router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Сменить пароль пользователя

    - old_password: текущий пароль
    - new_password: новый пароль (минимум 6 символов)
    """

    # Проверка длины нового пароля
    if len(new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Новый пароль должен быть не менее 6 символов"
        )

    # Проверка старого пароля
    old_pass_bytes = old_password.encode('utf-8')
    hash_bytes = current_user.password_hash.encode('utf-8')
    if not bcrypt.checkpw(old_pass_bytes, hash_bytes):
        raise HTTPException(
            status_code=400,
            detail="Неверный текущий пароль"
        )

    # Хеширование нового пароля
    new_pass_bytes = new_password.encode('utf-8')
    new_password_hash = bcrypt.hashpw(
        new_pass_bytes,
        bcrypt.gensalt()
    ).decode('utf-8')

    # Обновление пароля
    current_user.password_hash = new_password_hash
    db.commit()

    return {"message": "Пароль успешно изменен"}