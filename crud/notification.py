from sqlalchemy.orm import Session
from models.base import Notification, Mention, User
import re

class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, user_id: int, notification_type: str, title: str, 
               content: str = None, related_message_id: int = None, 
               related_user_id: int = None, related_space_id: int = None):
        """Создать уведомление"""
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            content=content,
            related_message_id=related_message_id,
            related_user_id=related_user_id,
            related_space_id=related_space_id
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification
    
    def get_user_notifications(self, user_id: int, unread_only: bool = False, limit: int = 50):
        """Получить уведомления пользователя"""
        query = self.db.query(Notification).filter(Notification.user_id == user_id)
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        return query.order_by(Notification.created_at.desc()).limit(limit).all()
    
    def mark_as_read(self, notification_id: int, user_id: int):
        """Пометить уведомление как прочитанное"""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if notification:
            notification.is_read = True
            self.db.commit()
            return True
        
        return False
    
    def mark_all_as_read(self, user_id: int):
        """Пометить все уведомления как прочитанные"""
        self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({"is_read": True})
        self.db.commit()
    
    def get_unread_count(self, user_id: int) -> int:
        """Получить количество непрочитанных уведомлений"""
        return self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()


class MentionRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def parse_mentions(self, content: str) -> list[str]:
        """Парсить @упоминания из текста"""
        # Ищем паттерн @nickname (буквы, цифры, подчёркивания)
        pattern = r'@(\w+)'
        mentions = re.findall(pattern, content)
        return list(set(mentions))  # Уникальные
    
    def create_mentions(self, message_id: int, content: str, author_id: int, chat_id: int):
        """Создать упоминания и уведомления"""
        nicknames = self.parse_mentions(content)
        
        if not nicknames:
            return []
        
        # Находим пользователей по никнеймам
        users = self.db.query(User).filter(User.nickname.in_(nicknames)).all()
        
        mentioned_users = []
        notification_repo = NotificationRepository(self.db)
        
        for user in users:
            # Не упоминаем самого себя
            if user.id == author_id:
                continue
            
            # Создаём запись упоминания
            mention = Mention(
                message_id=message_id,
                mentioned_user_id=user.id
            )
            self.db.add(mention)
            
            # Создаём уведомление
            author = self.db.query(User).filter(User.id == author_id).first()
            notification_repo.create(
                user_id=user.id,
                notification_type="mention",
                title=f"{author.nickname} упомянул вас",
                content=content[:100],  # Первые 100 символов
                related_message_id=message_id,
                related_user_id=author_id
            )
            
            mentioned_users.append(user)
        
        self.db.commit()
        return mentioned_users
    
    def get_message_mentions(self, message_id: int):
        """Получить упоминания в сообщении"""
        mentions = self.db.query(Mention).filter(
            Mention.message_id == message_id
        ).all()
        
        users = []
        for mention in mentions:
            user = self.db.query(User).filter(User.id == mention.mentioned_user_id).first()
            if user:
                users.append({
                    "id": user.id,
                    "nickname": user.nickname
                })
        
        return users