from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session

from schemas.space import SpaceCreate, SpaceOut, BanCreate
from utils.auth import get_current_user, check_permissions, get_db
from models.base import User, Space
from crud.space import SpaceRepository
from crud.ban import BanRepository
from crud.role import RoleRepository

router = APIRouter()

@router.post("/", response_model=SpaceOut)
async def create_space(
    space: SpaceCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создание новой комнаты"""
    space_repo = SpaceRepository(db)
    new_space = space_repo.create(
        space.name, 
        space.description or None, 
        current_user.id, 
        space.background_url or None
    )
    return new_space

@router.get("/")
async def get_all_spaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список всех комнат с chat_id"""
    from models.base import Chat
    
    spaces = db.query(Space).all()
    
    # chat_id для каждой комнаты
    result = []
    for space in spaces:
        # групповой чат по ID (если ID совпадают с пространством)
        chat = db.query(Chat).filter(
            Chat.id == space.id,
            Chat.type == "group"
        ).first()
        
        result.append({
            "id": space.id,
            "name": space.name,
            "description": space.description,
            "admin_id": space.admin_id,
            "chat_id": chat.id if chat else None
        })
    
    return result

@router.get("/{space_id}", response_model=SpaceOut)
async def get_space(
    space_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить информацию о комнате"""
    space_repo = SpaceRepository(db)
    space = space_repo.get_by_id(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    return space

@router.post("/{space_id}/join")
async def join_space(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Присоединиться к комнате"""
    space_repo = SpaceRepository(db)
    ban_repo = BanRepository(db)
    
    # проверка на бан
    if ban_repo.is_active(current_user.id, space_id):
        raise HTTPException(status_code=403, detail="Вы забанены в этом пространстве")
    
    # присоединение к комнате
    result = space_repo.join(space_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    
    return {"message": "Вы успешно присоединились к комнате"}

@router.get("/{space_id}/participants")
async def get_participants(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить участников комнаты"""
    space_repo = SpaceRepository(db)
    participants = space_repo.get_participants(space_id)
    
    return {
        "space_id": space_id,
        "participants": [
            {
                "id": user.id,
                "nickname": user.nickname,
                "status": user.status
            } for user in participants
        ]
    }

@router.delete("/{space_id}/kick/{user_id}")
async def kick_user(
    space_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Исключить пользователя из комнаты"""
    space_repo = SpaceRepository(db)
    role_repo = RoleRepository(db)
    
    # проверка прав (упрощённая - только админ может кикать)
    space = space_repo.get_by_id(space_id)
    if not space or space.admin_id != current_user.id:
        raise HTTPException(status_code=403, detail="У вас нет прав на это действие")
    
    space_repo.kick(space_id, user_id)
    return {"message": "Пользователь исключён из комнаты"}

@router.post("/{space_id}/ban/{user_id}")
async def ban_user(
    space_id: int,
    user_id: int,
    ban_data: BanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Забанить пользователя в комнате"""
    space_repo = SpaceRepository(db)
    ban_repo = BanRepository(db)
    
    # проверка прав (только админ)
    space = space_repo.get_by_id(space_id)
    if not space or space.admin_id != current_user.id:
        raise HTTPException(status_code=403, detail="У вас нет прав на бан")
    
    # создание бана
    ban_repo.create(
        user_id, 
        current_user.id, 
        space_id, 
        ban_data.reason or None, 
        ban_data.until
    )
    
    # кик пользователя
    space_repo.kick(space_id, user_id)
    
    return {"message": "Пользователь забанен"}

@router.get("/{space_id}/roles")
async def get_space_roles(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список ролей комнаты"""
    from models.base import Role
    
    roles = db.query(Role).filter(Role.space_id == space_id).all()
    
    return [{
        "id": role.id,
        "name": role.name,
        "permissions": role.permissions,
        "color": role.color
    } for role in roles]

@router.post("/{space_id}/assign-role/{user_id}/{role_id}")
async def assign_role(
    space_id: int,
    user_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Назначить роль пользователю"""
    from models.permissions import Permission
    
    role_repo = RoleRepository(db)
    
    # проверка прав - нужно разрешение MANAGE_ROLES
    if not role_repo.check_permission(current_user.id, space_id, Permission.MANAGE_ROLES):
        raise HTTPException(status_code=403, detail="У вас нет прав на назначение ролей")
    
    role_repo.assign_to_user(user_id, role_id)
    return {"message": "Роль успешно назначена"}