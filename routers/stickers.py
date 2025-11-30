from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from utils.auth import get_current_user, get_db
from utils.file_upload import FileUploader
from models.base import User, StickerPack, Sticker, UserStickerPack

router = APIRouter()

@router.get("/packs")
async def get_public_packs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить публичные паки стикеров"""
    packs = db.query(StickerPack).filter(StickerPack.is_public == True).all()
    
    result = []
    for pack in packs:
        sticker_count = db.query(Sticker).filter(Sticker.pack_id == pack.id).count()
        result.append({
            "id": pack.id,
            "name": pack.name,
            "description": pack.description,
            "thumbnail_url": pack.thumbnail_url,
            "sticker_count": sticker_count,
            "author_id": pack.author_id
        })
    
    return result

@router.get("/packs/{pack_id}")
async def get_pack_stickers(
    pack_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить стикеры из пака"""
    pack = db.query(StickerPack).filter(StickerPack.id == pack_id).first()
    
    if not pack:
        raise HTTPException(status_code=404, detail="Пак не найден")
    
    stickers = db.query(Sticker).filter(
        Sticker.pack_id == pack_id
    ).order_by(Sticker.sort_order).all()
    
    return {
        "pack": {
            "id": pack.id,
            "name": pack.name,
            "description": pack.description,
            "thumbnail_url": pack.thumbnail_url
        },
        "stickers": [{
            "id": s.id,
            "name": s.name,
            "image_url": s.image_url,
            "emoji_shortcode": s.emoji_shortcode
        } for s in stickers]
    }

@router.get("/my-packs")
async def get_my_packs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить установленные паки пользователя"""
    user_packs = db.query(UserStickerPack).filter(
        UserStickerPack.user_id == current_user.id
    ).all()
    
    result = []
    for up in user_packs:
        pack = db.query(StickerPack).filter(StickerPack.id == up.pack_id).first()
        if pack:
            result.append({
                "id": pack.id,
                "name": pack.name,
                "thumbnail_url": pack.thumbnail_url,
                "added_at": up.added_at
            })
    
    return result

@router.post("/packs/{pack_id}/install")
async def install_pack(
    pack_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Установить пак стикеров"""
    # проверка что пак существует
    pack = db.query(StickerPack).filter(StickerPack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail="Пак не найден")
    
    # проверка что ещё не установлен
    existing = db.query(UserStickerPack).filter(
        UserStickerPack.user_id == current_user.id,
        UserStickerPack.pack_id == pack_id
    ).first()
    
    if existing:
        return {"message": "Пак уже установлен"}
    
    # установка
    user_pack = UserStickerPack(user_id=current_user.id, pack_id=pack_id)
    db.add(user_pack)
    db.commit()
    
    return {"message": "Пак установлен"}

@router.delete("/packs/{pack_id}/uninstall")
async def uninstall_pack(
    pack_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить пак стикеров"""
    user_pack = db.query(UserStickerPack).filter(
        UserStickerPack.user_id == current_user.id,
        UserStickerPack.pack_id == pack_id
    ).first()
    
    if not user_pack:
        raise HTTPException(status_code=404, detail="Пак не установлен")
    
    db.delete(user_pack)
    db.commit()
    
    return {"message": "Пак удалён"}

@router.post("/packs/create")
async def create_pack(
    name: str,
    description: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать пак стикеров"""
    pack = StickerPack(
        name=name,
        description=description,
        author_id=current_user.id,
        is_public=True
    )
    db.add(pack)
    db.commit()
    db.refresh(pack)
    
    return {"id": pack.id, "name": pack.name}

@router.post("/packs/{pack_id}/add-sticker")
async def add_sticker_to_pack(
    pack_id: int,
    file: UploadFile = File(...),
    name: str = None,
    emoji_shortcode: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Добавить стикер в пак"""
    # проверка что пак существует и принадлежит пользователю
    pack = db.query(StickerPack).filter(
        StickerPack.id == pack_id,
        StickerPack.author_id == current_user.id
    ).first()
    
    if not pack:
        raise HTTPException(status_code=404, detail="Пак не найден или нет доступа")
    
    # загрузка изображения
    file_info = await FileUploader.upload_image(file)
    
    # получаем следующий sort_order
    max_order = db.query(Sticker).filter(Sticker.pack_id == pack_id).count()
    
    # создание стикера
    sticker = Sticker(
        pack_id=pack_id,
        name=name or file.filename,
        image_url=file_info["url"],
        emoji_shortcode=emoji_shortcode,
        sort_order=max_order
    )
    db.add(sticker)
    db.commit()
    db.refresh(sticker)
    
    return {
        "id": sticker.id,
        "name": sticker.name,
        "image_url": sticker.image_url
    }