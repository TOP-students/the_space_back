from sqlalchemy.orm import Session
from sqlalchemy import and_
from ..models.base import User, get_password_hash

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, nickname: str, email: str, password: str):
        hashed_password = get_password_hash(password)
        user = User(nickname=nickname, email=email, password_hash=hashed_password)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_nickname(self, nickname: str):
        return self.db.query(User).filter(User.nickname == nickname).first()

    def get_by_id(self, user_id: int):
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()

    def update_status(self, user_id: int, status: str):
        user = self.get_by_id(user_id)
        if user:
            user.status = status
            self.db.commit()
        return user