from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from utils.auth import get_current_user, get_db
from models.base import User
from models.permissions import Permission, get_permission_info
from crud.role import RoleRepository

router = APIRouter()

class RoleCreate(BaseModel):
    name: str
    permissions: List[str]
    color: Optional[str] = "#808080"
    priority: Optional[int] = 50

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    permissions: Optional[List[str]] = None
    color: Optional[str] = None
    priority: Optional[int] = None

@router.get("/{space_id}/roles")
async def get_space_roles(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список ролей комнаты с иерархией"""
    role_repo = RoleRepository(db)
    
    # проверка доступа к комнате
    if not role_repo.get_user_role(current_user.id, space_id):
        raise HTTPException(status_code=403, detail="Вы не участник этой комнаты")
    
    hierarchy = role_repo.get_role_hierarchy(space_id)
    return hierarchy

@router.get("/{space_id}/permissions")
async def get_available_permissions(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список всех доступных разрешений (для UI)"""
    role_repo = RoleRepository(db)
    
    if not role_repo.get_user_role(current_user.id, space_id):
        raise HTTPException(status_code=403, detail="Вы не участник этой комнаты")
    
    # группируем разрешения
    grouped = {}
    for group_key, group_data in Permission.GROUPS.items():
        grouped[group_key] = {
            "name": group_data["name"],
            "permissions": [
                {
                    "key": perm,
                    **get_permission_info(perm)
                } for perm in group_data["permissions"]
            ]
        }
    
    return grouped

# @router.get("/{space_id}/my-permissions")
# async def get_my_permissions(
#     space_id: int,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Получить мои разрешения в комнате"""
#     role_repo = RoleRepository(db)
    
#     role = role_repo.get_user_role(current_user.id, space_id)
#     if not role:
#         raise HTTPException(status_code=403, detail="Вы не участник этой комнаты")
    
#     permissions = role_repo.get_permissions(current_user.id, space_id)
    
#     return {
#         "role": {
#             "id": role.id,
#             "name": role.name,
#             "color": role.color,
#             "priority": role.priority
#         },
#         "permissions": permissions
#     }

# @router.post("/{space_id}/roles")
# async def create_role(
#     space_id: int,
#     role_data: RoleCreate,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Создать новую роль"""
#     role_repo = RoleRepository(db)
    
#     # проверка прав
#     if not role_repo.check_permission(current_user.id, space_id, Permission.PROMOTE_MEMBERS):
#         raise HTTPException(status_code=403, detail="У вас нет прав на создание ролей")
    
#     # проверка что разрешения валидны
#     invalid_perms = [p for p in role_data.permissions if p not in Permission.ALL]
#     if invalid_perms:
#         raise HTTPException(status_code=400, detail=f"Неизвестные разрешения: {invalid_perms}")
    
#     # создание роли
#     new_role = role_repo.create(
#         space_id=space_id,
#         name=role_data.name,
#         permissions=role_data.permissions,
#         color=role_data.color,
#         priority=role_data.priority,
#         is_system=False
#     )
    
#     return {
#         "id": new_role.id,
#         "name": new_role.name,
#         "permissions": new_role.permissions,
#         "color": new_role.color,
#         "priority": new_role.priority
#     }

@router.patch("/{space_id}/roles/{role_id}")
async def update_role(
    space_id: int,
    role_id: int,
    role_data: RoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить роль"""
    role_repo = RoleRepository(db)
    
    # проверка прав
    if not role_repo.check_permission(current_user.id, space_id, Permission.PROMOTE_MEMBERS):
        raise HTTPException(status_code=403, detail="У вас нет прав на изменение ролей")
    
    # проверка что может управлять этой ролью
    if not role_repo.can_manage_role(current_user.id, role_id, space_id):
        raise HTTPException(status_code=403, detail="Вы не можете изменять эту роль")
    
    # обновление
    updated_role = role_repo.update(
        role_id=role_id,
        name=role_data.name,
        permissions=role_data.permissions,
        color=role_data.color,
        priority=role_data.priority
    )
    
    if not updated_role:
        raise HTTPException(status_code=400, detail="Не удалось обновить роль")
    
    return {
        "id": updated_role.id,
        "name": updated_role.name,
        "permissions": updated_role.permissions,
        "color": updated_role.color,
        "priority": updated_role.priority
    }

@router.delete("/{space_id}/roles/{role_id}")
async def delete_role(
    space_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить роль"""
    role_repo = RoleRepository(db)
    
    # проверка прав
    if not role_repo.check_permission(current_user.id, space_id, Permission.PROMOTE_MEMBERS):
        raise HTTPException(status_code=403, detail="У вас нет прав на удаление ролей")
    
    # проверка что может управлять этой ролью
    if not role_repo.can_manage_role(current_user.id, role_id, space_id):
        raise HTTPException(status_code=403, detail="Вы не можете удалить эту роль")
    
    success = role_repo.delete(role_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Не удалось удалить роль")
    
    return {"message": "Роль удалена"}

@router.post("/{space_id}/members/{user_id}/role")
async def assign_role_to_member(
    space_id: int,
    user_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Назначить роль участнику"""
    role_repo = RoleRepository(db)
    
    # проверка прав
    if not role_repo.check_permission(current_user.id, space_id, Permission.PROMOTE_MEMBERS):
        raise HTTPException(status_code=403, detail="У вас нет прав на назначение ролей")
    
    # назначение
    result = role_repo.assign_to_user(user_id, role_id, assigner_id=current_user.id)
    
    if not result:
        raise HTTPException(status_code=400, detail="Не удалось назначить роль")
    
    return {"message": "Роль назначена"}

@router.get("/{space_id}/roles/{role_id}/members")
async def get_role_members(
    space_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить участников с определённой ролью"""
    role_repo = RoleRepository(db)
    
    # проверка доступа
    if not role_repo.get_user_role(current_user.id, space_id):
        raise HTTPException(status_code=403, detail="Вы не участник этой комнаты")
    
    members = role_repo.get_members_with_role(role_id)
    
    return [{
        "id": user.id,
        "nickname": user.nickname,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url
    } for user in members]

def get_role_hierarchy(self, space_id: int):
        """Получить иерархию ролей для UI"""
        roles = self.get_by_space(space_id)
        
        return [{
            "id": role.id,
            "name": role.name,
            "color": role.color,
            "priority": role.priority,
            "is_system": role.is_system,
            "member_count": self.db.query(UserRole).filter(UserRole.role_id == role.id).count(),
            "permissions": role.permissions
        } for role in roles]