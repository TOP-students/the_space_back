"""
Система разрешений для комнат
"""

# базовые разрешения
class Permission:
    # сообщения
    SEND_MESSAGES = "send_messages"
    DELETE_OWN_MESSAGES = "delete_own_messages"
    DELETE_ANY_MESSAGES = "delete_any_messages"
    EDIT_OWN_MESSAGES = "edit_own_messages"
    
    # участники
    KICK_MEMBERS = "kick_members"
    BAN_MEMBERS = "ban_members"
    MANAGE_ROLES = "manage_roles"
    VIEW_MEMBERS = "view_members"
    INVITE_MEMBERS = "invite_members"
    
    # комната
    MANAGE_SPACE = "manage_space"  # редактировать название, описание
    DELETE_SPACE = "delete_space"
    
    # все разрешения
    ALL = [
        SEND_MESSAGES,
        DELETE_OWN_MESSAGES,
        DELETE_ANY_MESSAGES,
        EDIT_OWN_MESSAGES,
        KICK_MEMBERS,
        BAN_MEMBERS,
        MANAGE_ROLES,
        VIEW_MEMBERS,
        INVITE_MEMBERS,
        MANAGE_SPACE,
        DELETE_SPACE,
    ]


# предустановленные роли
class RolePreset:
    OWNER = {
        "name": "Владелец",
        "permissions": Permission.ALL,
        "color": "#FF0000"
    }
    
    MODERATOR = {
        "name": "Модератор",
        "permissions": [
            Permission.SEND_MESSAGES,
            Permission.DELETE_OWN_MESSAGES,
            Permission.DELETE_ANY_MESSAGES,
            Permission.EDIT_OWN_MESSAGES,
            Permission.KICK_MEMBERS,
            Permission.BAN_MEMBERS,
            Permission.VIEW_MEMBERS,
            Permission.INVITE_MEMBERS,
        ],
        "color": "#00FF00"
    }
    
    MEMBER = {
        "name": "Участник",
        "permissions": [
            Permission.SEND_MESSAGES,
            Permission.DELETE_OWN_MESSAGES,
            Permission.EDIT_OWN_MESSAGES,
            Permission.VIEW_MEMBERS,
        ],
        "color": "#0000FF"
    }


def has_permission(user_permissions: list, required_permission: str) -> bool:
    """Проверить наличие разрешения у пользователя"""
    return required_permission in user_permissions