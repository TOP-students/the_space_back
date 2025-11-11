from sqlalchemy.orm import Session, joinedload
import json

from models.base import Role, UserRole
from models.permissions import has_permission

class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, space_id: int, name: str, permissions: list, color: str):
        role = Role(
            space_id=space_id, 
            name=name, 
            permissions=permissions,
            color=color
        )
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def get_by_id(self, role_id: int):
        return self.db.query(Role).filter(Role.id == role_id).first()
    
    def get_by_space(self, space_id: int):
        """Получить все роли комнаты"""
        return self.db.query(Role).filter(Role.space_id == space_id).all()

    def assign_to_user(self, user_id: int, role_id: int):
        # удаление старых ролей в комнате
        role = self.get_by_id(role_id)
        if role:
            self.db.query(UserRole).filter(
                UserRole.user_id == user_id,
                UserRole.role_id.in_(
                    self.db.query(Role.id).filter(Role.space_id == role.space_id)
                )
            ).delete(synchronize_session=False)
        
        # добавление новой роли
        existing = self.db.query(UserRole).filter(
            UserRole.user_id == user_id, 
            UserRole.role_id == role_id
        ).first()
        
        if not existing:
            user_role = UserRole(user_id=user_id, role_id=role_id)
            self.db.add(user_role)
            self.db.commit()
            self.db.refresh(user_role)
            return user_role
        
        return existing

    def get_permissions(self, user_id: int, space_id: int):
        """Получить разрешения пользователя в комнате"""
        user_role = (
        self.db.query(UserRole)
        .options(joinedload(UserRole.role))
        .join(Role, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id, Role.space_id == space_id)
        .first()
    )

        if user_role and user_role.role and isinstance(user_role.role.permissions, list):
            return user_role.role.permissions

        return []
    
    def check_permission(self, user_id: int, space_id: int, permission: str) -> bool:
        """Проверить наличие разрешения"""
        permissions = self.get_permissions(user_id, space_id)
        return has_permission(permissions, permission)