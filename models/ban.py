from sqlalchemy import Column, Text, DateTime, BigInteger, ForeignKey
from sqlalchemy.sql import func

from models.base import Base


class Ban(Base):
    __tablename__ = "bans"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    banned_by = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    space_id = Column(BigInteger, ForeignKey("spaces.id"))
    reason = Column(Text)
    until = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
