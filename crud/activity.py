from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from models.base import UserActivity, User

class ActivityRepository:
    def __init__(self, db: Session):
        self.db = db
    
    ONLINE_THRESHOLD_MINUTES = 5  # Если активность < 5 минут назад - онлайн
    AWAY_THRESHOLD_MINUTES = 15   # Если активность 5-15 минут - away
    
    def update_activity(self, user_id: int, status: str = "online", device_info: str = None):
        """Обновить активность пользователя"""
        activity = self.db.query(UserActivity).filter(
            UserActivity.user_id == user_id
        ).first()
        
        now = datetime.now()  # Без timezone
        
        if activity:
            activity.last_seen = now
            activity.status = status
            activity.is_active = (status == "online")
            if device_info:
                activity.device_info = device_info
        else:
            activity = UserActivity(
                user_id=user_id,
                last_seen=now,
                status=status,
                is_active=(status == "online"),
                device_info=device_info
            )
            self.db.add(activity)
        
        self.db.commit()
        self.db.refresh(activity)
        return activity
    
    def update_last_seen(self, user_id: int):
        """Обновить только время последней активности без изменения статуса"""
        activity = self.db.query(UserActivity).filter(
            UserActivity.user_id == user_id
        ).first()

        now = datetime.now()  # Без timezone

        if activity:
            activity.last_seen = now
            # НЕ меняем статус, только обновляем время
        else:
            # Если записи активности нет - проверяем статус в User
            user = self.db.query(User).filter(User.id == user_id).first()
            initial_status = user.status if user and user.status else "online"

            activity = UserActivity(
                user_id=user_id,
                last_seen=now,
                status=initial_status,
                is_active=(initial_status == "online")
            )
            self.db.add(activity)

        self.db.commit()
        self.db.refresh(activity)
        return activity

    def set_status(self, user_id: int, status: str):
        """Установить статус пользователя"""
        valid_statuses = ["online", "offline", "away", "dnd"]
        if status not in valid_statuses:
            return None

        # Обновляем статус в таблице User для сохранения между сессиями
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.status = status
            self.db.commit()

        return self.update_activity(user_id, status)
    
    def get_user_status(self, user_id: int) -> dict:
        """Получить статус пользователя"""
        activity = self.db.query(UserActivity).filter(
            UserActivity.user_id == user_id
        ).first()

        if not activity:
            # Если нет записи активности - берем статус из User
            user = self.db.query(User).filter(User.id == user_id).first()
            user_status = user.status if user and user.status else "offline"
            return {
                "status": user_status,
                "last_seen": None,
                "is_active": False
            }

        # Проверяем время последней активности
        now = datetime.now()  # Без timezone
        time_since_active = (now - activity.last_seen).total_seconds() / 60

        # Если пользователь установил статус вручную (away, dnd, offline), сохраняем его
        # Только для online автоматически меняем на offline при долгом отсутствии
        if activity.status in ["away", "dnd", "offline"]:
            # Статусы установленные вручную не меняются автоматически
            status = activity.status
            is_active = False
        elif time_since_active < self.ONLINE_THRESHOLD_MINUTES:
            # Если недавно был активен и статус online - остается online
            status = "online"
            is_active = True
        else:
            # Если долго не было активности и статус был online - меняем на offline
            status = "offline"
            is_active = False

        return {
            "status": status,
            "last_seen": activity.last_seen,
            "is_active": is_active,
            "device_info": activity.device_info
        }
    
    def get_online_users(self, space_id: int = None):
        """Получить список онлайн пользователей"""
        threshold = datetime.now() - timedelta(minutes=self.ONLINE_THRESHOLD_MINUTES)
        
        query = self.db.query(User).join(UserActivity).filter(
            UserActivity.last_seen >= threshold,
            UserActivity.status.in_(["online", "away"])
        )
        
        # Если указана комната - только участники этой комнаты
        if space_id:
            from models.base import ChatParticipant, Chat
            query = query.join(ChatParticipant, User.id == ChatParticipant.user_id).join(
                Chat, ChatParticipant.chat_id == Chat.id
            ).filter(
                Chat.space_id == space_id,
                ChatParticipant.is_active == True
            )
        
        users = query.distinct().all()
        
        result = []
        for user in users:
            status_info = self.get_user_status(user.id)
            result.append({
                "id": user.id,
                "nickname": user.nickname,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                **status_info
            })
        
        return result
    
    def cleanup_old_activities(self, days: int = 30):
        """Очистить старые записи активности (для maintenance)"""
        threshold = datetime.now() - timedelta(days=days)
        
        self.db.query(UserActivity).filter(
            UserActivity.last_seen < threshold,
            UserActivity.status == "offline"
        ).delete()
        
        self.db.commit()
    
    def get_users_by_status(self, status: str, limit: int = 100):
        """Получить пользователей по статусу"""
        threshold = datetime.now() - timedelta(minutes=self.ONLINE_THRESHOLD_MINUTES)
        
        if status == "online":
            activities = self.db.query(UserActivity).filter(
                UserActivity.last_seen >= threshold,
                UserActivity.status == "online"
            ).limit(limit).all()
        else:
            activities = self.db.query(UserActivity).filter(
                UserActivity.status == status
            ).limit(limit).all()
        
        result = []
        for activity in activities:
            user = self.db.query(User).filter(User.id == activity.user_id).first()
            if user:
                result.append({
                    "id": user.id,
                    "nickname": user.nickname,
                    "status": activity.status,
                    "last_seen": activity.last_seen
                })
        
        return result