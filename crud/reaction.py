from sqlalchemy.orm import Session
from sqlalchemy import func
from models.base import User, Reaction

class ReactionRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def add_reaction(self, message_id: int, user_id: int, reaction: str):
        """Добавить реакцию (или замена)"""
        # есть ли уже реакция этого пользователя на это сообщение
        existing = self.db.query(Reaction).filter(
            Reaction.message_id == message_id,
            Reaction.user_id == user_id
        ).first()
        
        if existing:
            # если та же реакция - удаляем (toggle)
            if existing.reaction == reaction:
                self.db.delete(existing)
                self.db.commit()
                return None
            # иначе меняем реакцию
            existing.reaction = reaction
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        # создаём новую реакцию
        new_reaction = Reaction(
            message_id=message_id,
            user_id=user_id,
            reaction=reaction
        )
        self.db.add(new_reaction)
        self.db.commit()
        self.db.refresh(new_reaction)
        
        return new_reaction
    
    def remove_reaction(self, message_id: int, user_id: int, reaction: str):
        """Удалить реакцию"""
        existing = self.db.query(Reaction).filter(
            Reaction.message_id == message_id,
            Reaction.user_id == user_id,
            Reaction.reaction == reaction
        ).first()
        
        if existing:
            self.db.delete(existing)
            self.db.commit()
            return True
        
        return False
    
    def get_message_reactions(self, message_id: int):
        """Получить все реакции на сообщение с группировкой"""
        # группируем реакции
        reactions_query = self.db.query(
            Reaction.reaction,
            func.count(Reaction.id).label('count')
        ).filter(
            Reaction.message_id == message_id
        ).group_by(Reaction.reaction).all()
        
        result = []
        for reaction, count in reactions_query:
            # получаем пользователей которые поставили эту реакцию
            users = self.db.query(User).join(Reaction).filter(
                Reaction.message_id == message_id,
                Reaction.reaction == reaction
            ).all()
            
            result.append({
                "reaction": reaction,
                "count": count,
                "users": [{"id": u.id, "nickname": u.nickname} for u in users]
            })
        
        return result
    
    def get_user_reaction(self, message_id: int, user_id: int):
        """Получить реакцию конкретного пользователя на сообщение"""
        reaction = self.db.query(Reaction).filter(
            Reaction.message_id == message_id,
            Reaction.user_id == user_id
        ).first()
        
        return reaction.reaction if reaction else None

    def get_reactions_for_messages(self, message_ids: list, current_user_id: int):
        """ОПТИМИЗАЦИЯ: Получить реакции для нескольких сообщений одним запросом"""
        if not message_ids:
            return {}, {}
        
        # Получаем все реакции для всех сообщений одним запросом
        all_reactions = self.db.query(Reaction, User).join(
            User, Reaction.user_id == User.id
        ).filter(
            Reaction.message_id.in_(message_ids)
        ).all()
        
        # Группируем реакции по message_id
        reactions_by_message = {}
        my_reactions = {}
        
        for reaction, user in all_reactions:
            msg_id = reaction.message_id
            
            if msg_id not in reactions_by_message:
                reactions_by_message[msg_id] = {}
            
            reaction_emoji = reaction.reaction
            if reaction_emoji not in reactions_by_message[msg_id]:
                reactions_by_message[msg_id][reaction_emoji] = {
                    "reaction": reaction_emoji,
                    "count": 0,
                    "users": []
                }
            
            reactions_by_message[msg_id][reaction_emoji]["count"] += 1
            reactions_by_message[msg_id][reaction_emoji]["users"].append({
                "id": user.id,
                "nickname": user.nickname
            })
            
            # Запоминаем реакцию текущего пользователя
            if user.id == current_user_id:
                my_reactions[msg_id] = reaction_emoji
        
        # Преобразуем в нужный формат
        result = {}
        for msg_id, reactions_dict in reactions_by_message.items():
            result[msg_id] = list(reactions_dict.values())
        
        return result, my_reactions