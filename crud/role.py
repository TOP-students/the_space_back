from sqlalchemy.orm import Session
from models.base import Role, UserRole, User
from models.permissions import has_permission, Permission

class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, space_id: int, name: str, permissions: list, color: str = None, 
               priority: int = 10, is_system: bool = False):
        """Создать кастомную роль"""
        role = Role(
            space_id=space_id, 
            name=name, 
            permissions=permissions,
            color=color or "#808080",
            priority=priority,
            is_system=is_system
        )
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def update(self, role_id: int, name: str = None, permissions: list = None, 
               color: str = None, priority: int = None):
        """Обновить роль"""
        role = self.get_by_id(role_id)
        
        if not role:
            return None
        
        # системные роли нельзя изменять
        if role.is_system:
            return None
        
        if name:
            role.name = name
        if permissions is not None:
            role.permissions = permissions
        if color:
            role.color = color
        if priority is not None:
            role.priority = priority
        
        self.db.commit()
        self.db.refresh(role)
        return role

    def delete(self, role_id: int):
        """Удалить роль"""
        role = self.get_by_id(role_id)
        
        if not role or role.is_system:
            return False
        
        # переназначить пользователей с этой ролью на роль по умолчанию (Участник)
        default_role = self.db.query(Role).filter(
            Role.space_id == role.space_id,
            Role.name == "Участник"
        ).first()
        
        if default_role:
            self.db.query(UserRole).filter(
                UserRole.role_id == role_id
            ).update({"role_id": default_role.id})
        
        self.db.delete(role)
        self.db.commit()
        return True

    def get_by_id(self, role_id: int):
        return self.db.query(Role).filter(Role.id == role_id).first()
    
    def get_by_space(self, space_id: int):
        """Получить все роли комнаты, отсортированные по приоритету"""
        return self.db.query(Role).filter(
            Role.space_id == space_id
        ).order_by(Role.priority.desc()).all()
    
    def get_default_role(self, space_id: int):
        """Получить роль по умолчанию (Участник)"""
        return self.db.query(Role).filter(
            Role.space_id == space_id,
            Role.name == "Участник"
        ).first()

    def assign_to_user(self, user_id: int, role_id: int, assigner_id: int = None):
        """Назначить роль пользователю"""
        role = self.get_by_id(role_id)
        if not role:
            return None
        
        # проверка прав назначающего (если указан)
        if assigner_id:
            assigner_role = self.get_user_role(assigner_id, role.space_id)
            target_role = self.get_user_role(user_id, role.space_id)
            
            # нельзя назначить роль выше своей
            if assigner_role and assigner_role.priority <= role.priority:
                return None
            
            # нельзя изменить роль пользователя с приоритетом выше/равным своему
            if target_role and target_role.priority >= assigner_role.priority:
                return None
        
        # удаляем старые роли в этой комнате
        self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id.in_(
                self.db.query(Role.id).filter(Role.space_id == role.space_id)
            )
        ).delete(synchronize_session=False)
        
        # добавляем новую роль
        user_role = UserRole(user_id=user_id, role_id=role_id)
        self.db.add(user_role)
        self.db.commit()
        self.db.refresh(user_role)
        
        return user_role
    
    def get_user_role(self, user_id: int, space_id: int):
        """Получить роль пользователя в комнате"""
        from models.base import ChatParticipant, Chat
        
        # проверяем что пользователь вообще участник комнаты
        is_participant = self.db.query(ChatParticipant).join(Chat).filter(
            Chat.space_id == space_id,
            ChatParticipant.user_id == user_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not is_participant:
            return None
        
        # получаем роль
        user_role = self.db.query(UserRole).join(Role).filter(
            UserRole.user_id == user_id, 
            Role.space_id == space_id
        ).first()
        
        # если роли нет - назначаем роль по умолчанию
        if not user_role:
            default_role = self.get_default_role(space_id)
            if default_role:
                self.assign_to_user(user_id, default_role.id)
                return default_role
            return None
        
        # Получаем объект Role
        role = self.db.query(Role).filter(Role.id == user_role.role_id).first()
        return role

    def get_permissions(self, user_id: int, space_id: int) -> list:
        """Получить разрешения пользователя в комнате"""
        role = self.get_user_role(user_id, space_id)
        
        if role and isinstance(role.permissions, list):
            return role.permissions
        
        return []
    
    def check_permission(self, user_id: int, space_id: int, permission: str) -> bool:
        """Проверить наличие разрешения"""
        permissions = self.get_permissions(user_id, space_id)
        return has_permission(permissions, permission)
    
    def can_manage_role(self, manager_id: int, target_role_id: int, space_id: int) -> bool:
        """Проверить может ли пользователь управлять ролью"""
        manager_role = self.get_user_role(manager_id, space_id)
        target_role = self.get_by_id(target_role_id)
        
        if not manager_role or not target_role:
            return False
        
        # нельзя управлять системными ролями (кроме владельца)
        if target_role.is_system and manager_role.name != "Владелец":
            return False
        
        # можно управлять только ролями с приоритетом ниже своего
        return manager_role.priority > target_role.priority
    
    def get_members_with_role(self, role_id: int):
        """Получить участников с определённой ролью"""
        user_roles = self.db.query(UserRole).filter(
            UserRole.role_id == role_id
        ).all()
        
        users = []
        for ur in user_roles:
            user = self.db.query(User).filter(User.id == ur.user_id).first()
            if user:
                users.append(user)
        
        return users
    
    def get_role_hierarchy(self, space_id: int):
        """Получить иерархию ролей для UI"""
        roles = self.get_by_space(space_id)
        
        return [{
            "id": role.id,
            "name": role.name,
            "color": role.color,
            "priority": role.priority,
            "is_system": role.is_system,
            "member_count": self.db.query(UserRole).filter(UserRole.role_id == role.id).count(),
            "permissions": role.permissions
        } for role in roles]