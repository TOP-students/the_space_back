from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..models.base import Ban

class BanRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, banned_by: int, space_id: int, reason: str, until: datetime):
        ban = Ban(user_id=user_id, banned_by=banned_by, space_id=space_id, reason=reason, until=until)
        self.db.add(ban)
        self.db.commit()
        self.db.refresh(ban)
        return ban

    def is_active(self, user_id: int, space_id: int):
        now = datetime.now(timezone.utc)
        return self.db.query(Ban).filter(
            Ban.user_id == user_id, Ban.space_id == space_id,
            or_(Ban.until > now, Ban.until.is_(None))
        ).first() is not None