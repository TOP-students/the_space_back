import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException
import os
from dotenv import load_dotenv

load_dotenv()

# конфигурация Cloudinary из переменных окружения
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# разрешённые типы файлов и размеры
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
ALLOWED_AUDIO_TYPES = ["audio/mpeg", "audio/wav", "audio/ogg"]
ALLOWED_DOCUMENT_TYPES = [
    "application/pdf", 
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain"
]

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

class FileUploader:
    @staticmethod
    async def upload_image(file: UploadFile) -> dict:
        """Загрузить изображение"""
        # проверка типа файла
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"Недопустимый тип файла. Разрешены: {', '.join(ALLOWED_IMAGE_TYPES)}"
            )
        
        # проверка размера
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Файл слишком большой. Максимум: {MAX_FILE_SIZE / (1024*1024)}MB"
            )
        
        # загрузка в Cloudinary
        try:
            result = cloudinary.uploader.upload(
                contents,
                folder="chat_images",
                resource_type="image"
            )
            
            return {
                "url": result["secure_url"],
                "public_id": result["public_id"],
                "width": result.get("width"),
                "height": result.get("height"),
                "format": result.get("format"),
                "size": len(contents)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {str(e)}")
    
    @staticmethod
    async def upload_audio(file: UploadFile) -> dict:
        """Загрузить аудио"""
        if file.content_type not in ALLOWED_AUDIO_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Недопустимый тип файла. Разрешены: {', '.join(ALLOWED_AUDIO_TYPES)}"
            )
        
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Файл слишком большой. Максимум: {MAX_FILE_SIZE / (1024*1024)}MB"
            )
        
        try:
            result = cloudinary.uploader.upload(
                contents,
                folder="chat_audio",
                resource_type="video"  # для аудио используем тип 'video'
            )
            
            return {
                "url": result["secure_url"],
                "public_id": result["public_id"],
                "format": result.get("format"),
                "size": len(contents),
                "duration": result.get("duration")
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {str(e)}")
    
    @staticmethod
    async def upload_document(file: UploadFile) -> dict:
        """Загрузить документ"""
        if file.content_type not in ALLOWED_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Недопустимый тип файла. Разрешены: PDF, DOC, DOCX, TXT"
            )
        
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Файл слишком большой. Максимум: {MAX_FILE_SIZE / (1024*1024)}MB"
            )
        
        try:
            result = cloudinary.uploader.upload(
                contents,
                folder="chat_documents",
                resource_type="raw"  # для документов используем 'raw'
            )
            
            return {
                "url": result["secure_url"],
                "public_id": result["public_id"],
                "format": result.get("format"),
                "size": len(contents),
                "filename": file.filename
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {str(e)}")
    
    @staticmethod
    async def upload_file(file: UploadFile) -> dict:
        """Универсальная загрузка (определяет тип автоматически)"""
        if file.content_type in ALLOWED_IMAGE_TYPES:
            return await FileUploader.upload_image(file)
        elif file.content_type in ALLOWED_AUDIO_TYPES:
            return await FileUploader.upload_audio(file)
        elif file.content_type in ALLOWED_DOCUMENT_TYPES:
            return await FileUploader.upload_document(file)
        else:
            raise HTTPException(
                status_code=400,
                detail="Неподдерживаемый тип файла"
            )