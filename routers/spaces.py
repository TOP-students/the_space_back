from fastapi import APIRouter, Depends, HTTPException
from typing import List

from schemas.space import SpaceCreate, SpaceOut, BanCreate
from utils.auth import get_current_user, check_permissions, get_db
from models.base import User
from crud.space import SpaceRepository
from crud.ban import BanRepository
from crud.role import RoleRepository
from fastapi import HTTPException

router = APIRouter()

@router.post("/", response_model=SpaceOut)
def create_space(space: SpaceCreate, current_user: User = Depends(get_current_user), space_repo: SpaceRepository = Depends(lambda: SpaceRepository(get_db()))):
    new_space = space_repo.create(space.name, space.description or None, current_user.id, space.background_url or None)
    return new_space

@router.post("/{space_id}/join")
def join_space(space_id: int, current_user: User = Depends(get_current_user), space_repo: SpaceRepository = Depends(lambda: SpaceRepository(get_db())), ban_repo: BanRepository = Depends(lambda: BanRepository(get_db()))):
    if ban_repo.is_active(current_user.id, space_id):
        raise HTTPException(status_code=403, detail="Вы забанены в этом пространстве")
    space_repo.join(space_id, current_user.id)
    return {"message": "Успешно присоединены к пространству"}

@router.get("/{space_id}/participants", response_model=List[SpaceOut])  # Адаптируйте под UserOut если нужно
def get_participants(space_id: int, current_user: User = Depends(get_current_user), space_repo: SpaceRepository = Depends(lambda: SpaceRepository(get_db()))):
    participants = space_repo.get_participants(space_id)
    return participants

@router.delete("/{space_id}/kick/{user_id}")
def kick_user(space_id: int, user_id: int, current_user: User = Depends(get_current_user), space_repo: SpaceRepository = Depends(lambda: SpaceRepository(get_db())), role_repo: RoleRepository = Depends(lambda: RoleRepository(get_db()))):
    db = get_db()
    if not check_permissions(db, current_user.id, space_id, "kick", role_repo):
        raise HTTPException(status_code=403, detail="У вас нет прав на кик")
    space_repo.kick(space_id, user_id)
    return {"message": "Пользователь успешно кикнут"}

@router.post("/{space_id}/ban/{user_id}")
def ban_user(space_id: int, user_id: int, ban_data: BanCreate, current_user: User = Depends(get_current_user), ban_repo: BanRepository = Depends(lambda: BanRepository(get_db())), role_repo: RoleRepository = Depends(lambda: RoleRepository(get_db()))):
    db = get_db()
    if not check_permissions(db, current_user.id, space_id, "ban", role_repo):
        raise HTTPException(status_code=403, detail="У вас нет прав на бан")
    ban_repo.create(user_id, current_user.id, space_id, ban_data.reason or None, ban_data.until)
    space_repo = SpaceRepository(db)
    space_repo.kick(space_id, user_id)
    return {"message": "Пользователь успешно забанен"}

@router.post("/{space_id}/assign-role/{user_id}/{role_id}")
def assign_role(space_id: int, user_id: int, role_id: int, current_user: User = Depends(get_current_user), role_repo: RoleRepository = Depends(lambda: RoleRepository(get_db()))):
    db = get_db()
    if not check_permissions(db, current_user.id, space_id, "assign_role", role_repo):
        raise HTTPException(status_code=403, detail="У вас нет прав на назначение ролей")
    role_repo.assign_to_user(user_id, role_id)
    return {"message": "Роль успешно назначена"}