from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session

from schemas.space import SpaceCreate, SpaceOut, BanCreate, RoleCreate, RoleOut
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
    from models.permissions import RolePreset

    space_repo = SpaceRepository(db)
    role_repo = RoleRepository(db)

    # Создаём пространство
    new_space = space_repo.create(
        space.name,
        space.description or None,
        current_user.id,
        space.background_url or None
    )

    # Создаём базовые роли
    owner_role = role_repo.create(
        new_space.id,
        RolePreset.OWNER["name"],
        RolePreset.OWNER["permissions"],
        RolePreset.OWNER["color"]
    )

    moderator_role = role_repo.create(
        new_space.id,
        RolePreset.MODERATOR["name"],
        RolePreset.MODERATOR["permissions"],
        RolePreset.MODERATOR["color"]
    )

    member_role = role_repo.create(
        new_space.id,
        RolePreset.MEMBER["name"],
        RolePreset.MEMBER["permissions"],
        RolePreset.MEMBER["color"]
    )

    # Назначаем создателю роль владельца
    role_repo.assign_to_user(current_user.id, owner_role.id)

    return new_space

@router.get("/")
async def get_all_spaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список комнат, где пользователь является активным участником"""
    from models.base import Chat, ChatParticipant

    # Получаем только те пространства, где пользователь - активный участник
    spaces = db.query(Space).join(
        Chat, Space.id == Chat.space_id
    ).join(
        ChatParticipant, Chat.id == ChatParticipant.chat_id
    ).filter(
        ChatParticipant.user_id == current_user.id,
        ChatParticipant.is_active == True
    ).all()

    # Добавляем chat_id для каждой комнаты
    result = []
    for space in spaces:
        chat = db.query(Chat).filter(
            Chat.space_id == space.id,
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
    from models.permissions import Permission, RoleHierarchy
    from models.base import Role, UserRole, Chat
    from utils.socketio_instance import sio

    space_repo = SpaceRepository(db)
    role_repo = RoleRepository(db)

    # Проверка существования пространства
    space = space_repo.get_by_id(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")

    # Проверка прав - админ или разрешение KICK_MEMBERS
    if not (space.admin_id == current_user.id or
            role_repo.check_permission(current_user.id, space_id, Permission.KICK_MEMBERS)):
        raise HTTPException(status_code=403, detail="У вас нет прав на исключение пользователей")

    # Нельзя кикнуть админа
    if user_id == space.admin_id:
        raise HTTPException(status_code=403, detail="Нельзя исключить администратора пространства")

    # Проверка иерархии ролей
    current_user_role = db.query(UserRole).join(Role).filter(
        UserRole.user_id == current_user.id,
        Role.space_id == space_id
    ).first()

    target_user_role = db.query(UserRole).join(Role).filter(
        UserRole.user_id == user_id,
        Role.space_id == space_id
    ).first()

    # Если не владелец, проверяем иерархию
    if space.admin_id != current_user.id:
        if not current_user_role or not current_user_role.role:
            raise HTTPException(status_code=403, detail="У вас нет роли в этом пространстве")

        if target_user_role and target_user_role.role:
            if not RoleHierarchy.can_moderate(current_user_role.role.name, target_user_role.role.name):
                raise HTTPException(status_code=403, detail="Вы не можете исключить пользователя с такой же или более высокой ролью")

    # Получаем информацию о пользователе для события
    kicked_user = db.query(User).filter(User.id == user_id).first()

    # Получаем chat_id пространства
    chat = db.query(Chat).filter(
        Chat.space_id == space_id,
        Chat.type == "group"
    ).first()

    space_repo.kick(space_id, user_id)

    # Отправляем WebSocket-событие о кике пользователя
    if chat and kicked_user:
        room_id = str(chat.id)
        await sio.emit('user_kicked', {
            'space_id': space_id,
            'room_id': room_id,
            'user_id': user_id,
            'nickname': kicked_user.nickname
        }, room=room_id)

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
    from models.permissions import Permission, RoleHierarchy
    from models.base import Role, UserRole

    space_repo = SpaceRepository(db)
    ban_repo = BanRepository(db)
    role_repo = RoleRepository(db)

    # Проверка существования пространства
    space = space_repo.get_by_id(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")

    # Проверка прав - админ или разрешение BAN_MEMBERS
    if not (space.admin_id == current_user.id or
            role_repo.check_permission(current_user.id, space_id, Permission.BAN_MEMBERS)):
        raise HTTPException(status_code=403, detail="У вас нет прав на бан пользователей")

    # Нельзя забанить админа
    if user_id == space.admin_id:
        raise HTTPException(status_code=403, detail="Нельзя забанить администратора пространства")

    # Проверка иерархии ролей
    current_user_role = db.query(UserRole).join(Role).filter(
        UserRole.user_id == current_user.id,
        Role.space_id == space_id
    ).first()

    target_user_role = db.query(UserRole).join(Role).filter(
        UserRole.user_id == user_id,
        Role.space_id == space_id
    ).first()

    # Если не владелец, проверяем иерархию
    if space.admin_id != current_user.id:
        if not current_user_role or not current_user_role.role:
            raise HTTPException(status_code=403, detail="У вас нет роли в этом пространстве")

        if target_user_role and target_user_role.role:
            if not RoleHierarchy.can_moderate(current_user_role.role.name, target_user_role.role.name):
                raise HTTPException(status_code=403, detail="Вы не можете забанить пользователя с такой же или более высокой ролью")

    # Создание бана
    ban_repo.create(
        user_id,
        current_user.id,
        space_id,
        ban_data.reason or None,
        ban_data.until
    )

    # Забаненный пользователь остается в чате, но не может писать
    return {"message": "Пользователь забанен"}

@router.delete("/{space_id}/unban/{user_id}")
async def unban_user(
    space_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Разбанить пользователя"""
    from models.permissions import Permission
    from crud.ban import BanRepository

    space_repo = SpaceRepository(db)
    ban_repo = BanRepository(db)
    role_repo = RoleRepository(db)

    # Проверка существования пространства
    space = space_repo.get_by_id(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")

    # Проверка прав - админ или разрешение BAN_MEMBERS
    if not (space.admin_id == current_user.id or
            role_repo.check_permission(current_user.id, space_id, Permission.BAN_MEMBERS)):
        raise HTTPException(status_code=403, detail="У вас нет прав на управление банами")

    # Удаляем бан
    removed = ban_repo.remove(user_id, space_id)

    if not removed:
        raise HTTPException(status_code=404, detail="Активный бан не найден")

    return {"message": "Пользователь разбанен"}

@router.get("/{space_id}/my-permissions")
async def get_my_permissions(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить права текущего пользователя в пространстве"""
    from models.base import Role, UserRole

    space_repo = SpaceRepository(db)
    role_repo = RoleRepository(db)

    # Проверка существования пространства
    space = space_repo.get_by_id(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")

    # Если пользователь - админ, возвращаем все права
    if space.admin_id == current_user.id:
        from models.permissions import Permission
        return {
            "is_admin": True,
            "permissions": Permission.ALL,
            "role": {"name": "Владелец", "color": "#FF0000"}
        }

    # Получаем роль пользователя
    permissions = role_repo.get_permissions(current_user.id, space_id)
    user_role = db.query(UserRole).join(Role).filter(
        UserRole.user_id == current_user.id,
        Role.space_id == space_id
    ).first()

    role_info = None
    if user_role and user_role.role:
        role_info = {
            "name": user_role.role.name,
            "color": user_role.role.color
        }

    return {
        "is_admin": False,
        "permissions": permissions,
        "role": role_info
    }

@router.post("/{space_id}/roles", response_model=RoleOut)
async def create_role(
    space_id: int,
    role_data: RoleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать кастомную роль (только для админов и модераторов с правами)"""
    from models.permissions import Permission

    role_repo = RoleRepository(db)
    space_repo = SpaceRepository(db)

    # Проверка существования пространства
    space = space_repo.get_by_id(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")

    # Проверка прав - нужно разрешение MANAGE_ROLES или быть админом
    if not (space.admin_id == current_user.id or
            role_repo.check_permission(current_user.id, space_id, Permission.MANAGE_ROLES)):
        raise HTTPException(status_code=403, detail="У вас нет прав на создание ролей")

    # Создаём роль
    new_role = role_repo.create(
        space_id,
        role_data.name,
        role_data.permissions or [],
        role_data.color or "#808080"
    )

    return new_role

@router.post("/{space_id}/assign-role/{user_id}/{role_id}")
async def assign_role(
    space_id: int,
    user_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Назначить роль пользователю"""
    from models.permissions import Permission, RoleHierarchy
    from models.base import Role, UserRole

    role_repo = RoleRepository(db)
    space_repo = SpaceRepository(db)

    # проверка прав - нужно разрешение MANAGE_ROLES
    if not role_repo.check_permission(current_user.id, space_id, Permission.MANAGE_ROLES):
        raise HTTPException(status_code=403, detail="У вас нет прав на назначение ролей")

    # Получаем роль, которую хотим назначить
    target_role = db.query(Role).filter(Role.id == role_id).first()
    if not target_role:
        raise HTTPException(status_code=404, detail="Роль не найдена")

    # Проверка пространства
    space = space_repo.get_by_id(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")

    # Если не владелец, проверяем иерархию
    if space.admin_id != current_user.id:
        # Получаем роль того, кто назначает
        current_user_role = db.query(UserRole).join(Role).filter(
            UserRole.user_id == current_user.id,
            Role.space_id == space_id
        ).first()

        if not current_user_role or not current_user_role.role:
            raise HTTPException(status_code=403, detail="У вас нет роли в этом пространстве")

        # Проверяем, может ли модератор назначать эту роль
        if not RoleHierarchy.can_moderate(current_user_role.role.name, target_role.name):
            raise HTTPException(status_code=403, detail="Вы не можете назначать роль такого же или более высокого уровня")

    role_repo.assign_to_user(user_id, role_id)
    return {"message": "Роль успешно назначена"}

@router.post("/{space_id}/add-user")
async def add_user_to_space(
    space_id: int,
    user_identifier: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Добавить пользователя в пространство по никнейму или ID"""
    space_repo = SpaceRepository(db)

    # Проверка прав - только админ может добавлять
    space = space_repo.get_by_id(space_id)
    if not space or space.admin_id != current_user.id:
        raise HTTPException(status_code=403, detail="У вас нет прав на добавление пользователей")

    # Ищем пользователя по ID или никнейму
    user_to_add = None
    if user_identifier.isdigit():
        user_to_add = db.query(User).filter(User.id == int(user_identifier)).first()
    else:
        user_to_add = db.query(User).filter(User.nickname == user_identifier).first()

    if not user_to_add:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Добавляем пользователя в пространство
    result = space_repo.join(space_id, user_to_add.id)
    if not result:
        raise HTTPException(status_code=404, detail="Пространство не найдено")

    return {
        "message": "Пользователь добавлен в пространство",
        "user": {
            "id": user_to_add.id,
            "nickname": user_to_add.nickname
        }
    }

@router.patch("/{space_id}/name")
async def update_space_name(
    space_id: int,
    new_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Изменить название пространства"""
    space_repo = SpaceRepository(db)

    # Проверка прав - только админ может изменять название
    space = space_repo.get_by_id(space_id)
    if not space or space.admin_id != current_user.id:
        raise HTTPException(status_code=403, detail="У вас нет прав на изменение названия")

    # Обновляем название
    space.name = new_name
    db.commit()

    return {
        "message": "Название пространства обновлено",
        "space": {
            "id": space.id,
            "name": space.name
        }
    }

@router.post("/{space_id}/leave")
async def leave_space(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Покинуть пространство (только для обычных участников, не админов)"""
    space_repo = SpaceRepository(db)

    # Проверяем существование пространства
    space = space_repo.get_by_id(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")

    # Админ не может покинуть свое пространство
    if space.admin_id == current_user.id:
        raise HTTPException(status_code=403, detail="Администратор не может покинуть пространство. Удалите пространство или передайте права администратора.")

    # Удаляем пользователя из участников (kick)
    space_repo.kick(space_id, current_user.id)

    return {"message": "Вы покинули пространство"}

@router.delete("/{space_id}/delete")
async def delete_space(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить пространство (только админ)"""
    from models.base import Chat, Message, ChatParticipant, Attachment

    space_repo = SpaceRepository(db)

    # Проверка прав - только админ может удалять
    space = space_repo.get_by_id(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Пространство не найдено")

    if space.admin_id != current_user.id:
        raise HTTPException(status_code=403, detail="Только администратор может удалить пространство")

    try:
        from models.base import Role, UserRole, Ban

        # Удаляем баны, связанные с пространством (у них нет CASCADE)
        db.query(Ban).filter(Ban.space_id == space_id).delete()

        # Удаляем роли пространства (это также удалит UserRole через CASCADE)
        db.query(Role).filter(Role.space_id == space_id).delete()

        # Находим связанный групповой чат
        chat = db.query(Chat).filter(
            Chat.space_id == space_id,
            Chat.type == "group"
        ).first()

        if chat:
            # Удаляем чат (это каскадно удалит Messages, Attachments, ChatParticipants)
            db.delete(chat)

        # Удаляем само пространство
        db.delete(space)
        db.commit()

        return {"message": "Пространство успешно удалено"}
    except Exception as e:
        db.rollback()
        print(f"Error deleting space: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении: {str(e)}")
