from sqlalchemy import Column, String, DateTime, BigInteger, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.base import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    space_id = Column(
        BigInteger,
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False
    )
    name = Column(String(50), nullable=False)
    permissions = Column(JSON)
    color = Column(String(7))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user_roles = relationship("UserRole", back_populates="role")


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    role_id = Column(
        BigInteger,
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False
    )
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    role = relationship("Role", back_populates="user_roles")
