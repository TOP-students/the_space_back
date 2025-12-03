from sqlalchemy.orm import Session

from models.base import Space, Chat, ChatParticipant, User, Role, UserRole

class SpaceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str, description: str, admin_id: int, background_url: str):
        # space
        space = Space(
            name=name,
            description=description,
            admin_id=admin_id,
            background_url=background_url
        )
        self.db.add(space)
        self.db.commit()
        self.db.refresh(space)

        # групповой чат для space
        chat = Chat(
            type="group",
            user1_id=admin_id,
            user2_id=admin_id,
            space_id=space.id
        )
        self.db.add(chat)
        self.db.commit()
        self.db.refresh(chat)

        # админ = участник чата
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

        # Назначаем роль "Участник" если у пользователя нет роли в этом пространстве
        existing_role = self.db.query(UserRole).join(Role).filter(
            UserRole.user_id == user_id,
            Role.space_id == space_id
        ).first()

        if not existing_role:
            # Находим роль "Участник"
            member_role = self.db.query(Role).filter(
                Role.space_id == space_id,
                Role.name == "Участник"
            ).first()

            if member_role:
                user_role = UserRole(user_id=user_id, role_id=member_role.id)
                self.db.add(user_role)

        self.db.commit()
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