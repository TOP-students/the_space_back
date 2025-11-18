import os
from typing import Optional
from supabase import create_client, Client
from io import BytesIO
from PIL import Image
import hashlib
from datetime import datetime

# Инициализация Supabase клиента
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "avatars")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def optimize_image(image_bytes: bytes, max_size: tuple = (800, 800), quality: int = 85) -> bytes:
    """
    Оптимизирует изображение: уменьшает размер и качество

    Args:
        image_bytes: Байты изображения
        max_size: Максимальный размер (ширина, высота)
        quality: Качество сжатия (1-100)

    Returns:
        Оптимизированные байты изображения
    """
    img = Image.open(BytesIO(image_bytes))

    # Конвертируем в RGB если нужно (для JPEG)
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background

    # Изменяем размер если нужно
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Сохраняем в буфер
    output = BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True)
    output.seek(0)

    return output.read()


def generate_unique_filename(user_id: int, file_type: str) -> str:
    """
    Генерирует уникальное имя файла

    Args:
        user_id: ID пользователя
        file_type: Тип файла ('avatar' или 'banner')

    Returns:
        Уникальное имя файла
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    hash_part = hashlib.md5(f"{user_id}{timestamp}".encode()).hexdigest()[:8]
    return f"{user_id}/{file_type}_{timestamp}_{hash_part}.jpg"


async def upload_image_to_storage(
    user_id: int,
    file_bytes: bytes,
    file_type: str,  # 'avatar' or 'banner'
    content_type: str = "image/jpeg"
) -> Optional[str]:
    """
    Загружает изображение в Supabase Storage

    Args:
        user_id: ID пользователя
        file_bytes: Байты файла
        file_type: Тип файла ('avatar' или 'banner')
        content_type: MIME тип файла

    Returns:
        Публичный URL загруженного файла или None при ошибке
    """
    try:
        print(f"🔄 Starting upload for user {user_id}, type: {file_type}")

        # Оптимизируем изображение
        if file_type == 'avatar':
            optimized_bytes = optimize_image(file_bytes, max_size=(400, 400), quality=85)
        else:  # banner
            optimized_bytes = optimize_image(file_bytes, max_size=(1200, 400), quality=90)

        print(f"📦 Image optimized: {len(optimized_bytes)} bytes")

        # Генерируем уникальное имя файла
        filename = generate_unique_filename(user_id, file_type)
        print(f"📝 Generated filename: {filename}")

        # Загружаем файл в Supabase Storage
        print(f"☁️  Uploading to bucket '{SUPABASE_BUCKET}'...")
        response = supabase.storage.from_(SUPABASE_BUCKET).upload(
            path=filename,
            file=optimized_bytes,
            file_options={"content-type": content_type, "upsert": "true"}
        )
        print(f"📤 Upload response: {response}")

        # Получаем публичный URL
        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(filename)
        print(f"🔗 Public URL generated: {public_url}")

        return public_url

    except Exception as e:
        print(f"❌ Error uploading image to storage: {e}")
        import traceback
        traceback.print_exc()
        return None


async def delete_image_from_storage(file_url: str) -> bool:
    """
    Удаляет изображение из Supabase Storage

    Args:
        file_url: URL файла для удаления

    Returns:
        True если успешно удалено, False при ошибке
    """
    try:
        # Извлекаем путь файла из URL
        # URL формат: https://project.supabase.co/storage/v1/object/public/bucket/path
        if "/object/public/" in file_url:
            path = file_url.split("/object/public/")[1]
            bucket_and_path = path.split("/", 1)
            if len(bucket_and_path) == 2:
                file_path = bucket_and_path[1]

                # Удаляем файл
                supabase.storage.from_(SUPABASE_BUCKET).remove([file_path])
                return True

        return False

    except Exception as e:
        print(f"Error deleting image from storage: {e}")
        return False
