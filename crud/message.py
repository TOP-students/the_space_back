from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, text
from models.base import Message, User

class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, chat_id: int, user_id: int, content: str, type: str, attachment_id: int = None):
        message = Message(
            chat_id=chat_id, 
            user_id=user_id, 
            content=content, 
            type=type, 
            attachment_id=attachment_id
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        message.user = self.db.query(User).filter(User.id == user_id).first()
        
        return message

    def get_by_id(self, message_id: int):
        return self.db.query(Message).filter(Message.id == message_id).first()

    def get_by_chat(self, chat_id: int, limit: int = 50, offset: int = 0):
        messages = self.db.query(Message).join(User).filter(
            Message.chat_id == chat_id, 
            Message.is_deleted == False
        ).order_by(Message.created_at.desc()).offset(offset).limit(limit).all()[::-1]
        
        for msg in messages:
            msg.user = self.db.query(User).filter(User.id == msg.user_id).first()
        
        return messages

    def search_by_chat(self, chat_id: int, query: str, limit: int = 50, offset: int = 0):
        messages = self.db.query(Message).filter(
            Message.chat_id == chat_id, 
            Message.is_deleted == False,
            Message.content.ilike(f"%{query}%")
        ).order_by(Message.created_at.desc()).offset(offset).limit(limit).all()[::-1]
        
        for msg in messages:
            msg.user = self.db.query(User).filter(User.id == msg.user_id).first()
        
        return messages

    def update(self, message_id: int, content: str, user_id: int):
        message = self.get_by_id(message_id)
        if message and message.user_id == user_id and not message.is_deleted:
            message.content = content
            self.db.commit()
            message.user = self.db.query(User).filter(User.id == user_id).first()
            return message
        return None

    def delete(self, message_id: int, user_id: int):
        message = self.get_by_id(message_id)
        if message and message.user_id == user_id and not message.is_deleted:
            message.is_deleted = True
            self.db.commit()
            return message
        return None