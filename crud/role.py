from sqlalchemy.orm import Session
import json
from ..models.base import Role, UserRole

class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, space_id: int, name: str, permissions: list, color: str):
        role = Role(space_id=space_id, name=name, permissions=json.dumps(permissions), color=color)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def get_by_id(self, role_id: int):
        return self.db.query(Role).filter(Role.id == role_id).first()

    def assign_to_user(self, user_id: int, role_id: int):
        existing = self.db.query(UserRole).filter(UserRole.user_id == user_id, UserRole.role_id == role_id).first()
        if not existing:
            user_role = UserRole(user_id=user_id, role_id=role_id)
            self.db.add(user_role)
            self.db.commit()
        return existing or user_role

    def get_permissions(self, user_id: int, space_id: int):
        user_role = self.db.query(UserRole).join(Role).filter(
            UserRole.user_id == user_id, Role.space_id == space_id
        ).first()
        if user_role:
            return json.loads(user_role.role.permissions) if user_role.role.permissions else []
        return []