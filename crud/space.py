from sqlalchemy.orm import Session

from models.base import Space, Chat, ChatParticipant, User, Role, UserRole
from models.permissions import RolePreset, Permission

class SpaceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str, description: str, admin_id: int, background_url: str):

        # создаём Space
        space = Space(
            name=name, 
            description=description, 
            admin_id=admin_id, 
            background_url=background_url
        )
        self.db.add(space)
        self.db.commit()
        self.db.refresh(space)
        
        # создаём групповой чат для Space
        chat = Chat(
            type="group",
            user1_id=admin_id,
            user2_id=admin_id,
            space_id=space.id
        )
        self.db.add(chat)
        self.db.commit()
        self.db.refresh(chat)
        
        # создаём стандартные роли
        from models.permissions import RolePreset
        
        owner_role = Role(
            space_id=space.id,
            name=RolePreset.OWNER["name"],
            permissions=RolePreset.OWNER["permissions"],
            color=RolePreset.OWNER["color"],
            priority=RolePreset.OWNER["priority"],
            is_system=RolePreset.OWNER["is_system"]
        )
        self.db.add(owner_role)
        
        moderator_role = Role(
            space_id=space.id,
            name=RolePreset.MODERATOR["name"],
            permissions=RolePreset.MODERATOR["permissions"],
            color=RolePreset.MODERATOR["color"],
            priority=RolePreset.MODERATOR["priority"],
            is_system=RolePreset.MODERATOR["is_system"]
        )
        self.db.add(moderator_role)
        
        member_role = Role(
            space_id=space.id,
            name=RolePreset.MEMBER["name"],
            permissions=RolePreset.MEMBER["permissions"],
            color=RolePreset.MEMBER["color"],
            priority=RolePreset.MEMBER["priority"],
            is_system=RolePreset.MEMBER["is_system"]
        )
        self.db.add(member_role)
        
        self.db.commit()
        self.db.refresh(owner_role)
        
        # ВАЖНО: Назначаем создателя владельцем
        user_role = UserRole(user_id=admin_id, role_id=owner_role.id)
        self.db.add(user_role)
        
        # добавление админа как участника
        participant = ChatParticipant(
            chat_id=chat.id, 
            user_id=admin_id, 
            is_active=True
        )
        self.db.add(participant)
        self.db.commit()
        
        return space

    def get_by_id(self, space_id: int):
        return self.db.query(Space).filter(Space.id == space_id).first()
    
    def get_space_chat(self, space_id: int):
        """Получить чат комнаты"""
        chat = self.db.query(Chat).filter(
            Chat.space_id == space_id
        ).first()
        
        return chat

    def get_participants(self, space_id: int):
        """Получить участников комнаты"""
        chat = self.get_space_chat(space_id)
        if not chat:
            return []
        
        participants = self.db.query(User).join(ChatParticipant).filter(
            ChatParticipant.chat_id == chat.id,
            ChatParticipant.is_active == True
        ).all()
        
        return participants
    
    def get_space_with_chat(self, space_id: int):
        """Получить комнату с chat_id"""
        space = self.get_by_id(space_id)
        if not space:
            return None
        
        chat = self.get_space_chat(space_id)
        
        return {
            "id": space.id,
            "name": space.name,
            "description": space.description,
            "admin_id": space.admin_id,
            "chat_id": chat.id if chat else None
        }

    def join(self, space_id: int, user_id: int):
        """Присоединиться к комнате"""
        space = self.get_by_id(space_id)
        if not space:
            return None
        
        chat = self.get_space_chat(space_id)
        if not chat:
            return None
        
        # проверяем, есть ли уже участник
        existing = self.db.query(ChatParticipant).filter(
            ChatParticipant.chat_id == chat.id, 
            ChatParticipant.user_id == user_id
        ).first()
        
        if existing:
            existing.is_active = True
        else:
            participant = ChatParticipant(
                chat_id=chat.id, 
                user_id=user_id, 
                is_active=True
            )
            self.db.add(participant)
        
        self.db.commit()
        
        # назначить роль по умолчанию
        from crud.role import RoleRepository
        role_repo = RoleRepository(self.db)
        
        # проверяем есть ли роль
        user_role = role_repo.get_user_role(user_id, space_id)
        if not user_role:
            # назначаем роль "Участник"
            default_role = role_repo.get_default_role(space_id)
            if default_role:
                role_repo.assign_to_user(user_id, default_role.id)
        
        return space

    def kick(self, space_id: int, user_id: int):
        """Удалить пользователя из комнаты"""
        chat = self.get_space_chat(space_id)
        if not chat:
            return None
        
        participant = self.db.query(ChatParticipant).filter(
            ChatParticipant.chat_id == chat.id, 
            ChatParticipant.user_id == user_id
        ).first()
        
        if participant:
            participant.is_active = False
            self.db.commit()
        
        return participant