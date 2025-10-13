from sqlalchemy.orm import Session
from ..main import Space, Chat, ChatParticipant

class SpaceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str, description: str, admin_id: int, background_url: str):
        space = Space(name=name, description=description, admin_id=admin_id, background_url=background_url)
        self.db.add(space)
        self.db.commit()
        self.db.refresh(space)
        
        # Автоматическое создание чата
        chat = Chat(type="group", user1_id=space.id, user2_id=admin_id)
        self.db.add(chat)
        self.db.commit()
        self.db.refresh(chat)
        
        # Добавление админа как участника
        participant = ChatParticipant(chat_id=chat.id, user_id=admin_id, is_active=True)
        self.db.add(participant)
        self.db.commit()
        
        space.chat_id = chat.id
        return space

    def get_by_id(self, space_id: int):
        return self.db.query(Space).filter(Space.id == space_id).first()

    def get_participants(self, space_id: int):
        chat = self.db.query(Chat).filter(Chat.user1_id == space_id).first()
        if not chat:
            return []
        return self.db.query(User).join(ChatParticipant).filter(
            ChatParticipant.chat_id == chat.id, ChatParticipant.is_active == True
        ).all()

    def join(self, space_id: int, user_id: int):
        space = self.get_by_id(space_id)
        if not space:
            return None
        chat = self.db.query(Chat).filter(Chat.user1_id == space_id).first()
        if not chat:
            return None
        existing = self.db.query(ChatParticipant).filter(
            ChatParticipant.chat_id == chat.id, ChatParticipant.user_id == user_id
        ).first()
        if existing:
            existing.is_active = True
        else:
            participant = ChatParticipant(chat_id=chat.id, user_id=user_id, is_active=True)
            self.db.add(participant)
        self.db.commit()
        return space

    def kick(self, space_id: int, user_id: int):
        chat = self.db.query(Chat).filter(Chat.user1_id == space_id).first()
        if not chat:
            return None
        participant = self.db.query(ChatParticipant).filter(
            ChatParticipant.chat_id == chat.id, ChatParticipant.user_id == user_id
        ).first()
        if participant:
            participant.is_active = False
            self.db.commit()
        return participant