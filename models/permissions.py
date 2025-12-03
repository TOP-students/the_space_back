"""
Продвинутая система разрешений для комнат
"""

class Permission:
    # === управление чатом ===
    CHANGE_INFO = "change_info"  # изменить название и аватар комнаты
    DELETE_SPACE = "delete_space"  # удалить комнату
    
    # === управление участниками ===
    ADD_MEMBERS = "add_members"  # добавлять участников
    BAN_MEMBERS = "ban_members"  # банить участников
    KICK_MEMBERS = "kick_members"  # удалять участников (без бана)
    RESTRICT_MEMBERS = "restrict_members"  # ограничивать права участников
    PROMOTE_MEMBERS = "promote_members"  # назначать администраторов
    
    # === сообщения ===
    SEND_MESSAGES = "send_messages"  # отправлять текстовые сообщения
    SEND_MEDIA = "send_media"  # отправлять медиа (фото, видео, аудио)
    SEND_STICKERS = "send_stickers"  # отправлять стикеры
    SEND_FILES = "send_files"  # отправлять файлы
    
    # === управление сообщениями ===
    EDIT_OWN_MESSAGES = "edit_own_messages"  # редактировать свои сообщения
    DELETE_OWN_MESSAGES = "delete_own_messages"  # удалять свои сообщения
    DELETE_ANY_MESSAGES = "delete_any_messages"  # удалять любые сообщения
    PIN_MESSAGES = "pin_messages"  # закреплять сообщения
    
    # === дополнительные возможности ===
    ADD_REACTIONS = "add_reactions"  # ставить реакции
    MENTION_ALL = "mention_all"  # упоминать @everyone
    CREATE_INVITES = "create_invites"  # создавать пригласительные ссылки
    
    # все разрешения
    ALL = [
        CHANGE_INFO, DELETE_SPACE,
        ADD_MEMBERS, BAN_MEMBERS, KICK_MEMBERS, RESTRICT_MEMBERS, PROMOTE_MEMBERS,
        SEND_MESSAGES, SEND_MEDIA, SEND_STICKERS, SEND_FILES,
        EDIT_OWN_MESSAGES, DELETE_OWN_MESSAGES, DELETE_ANY_MESSAGES, PIN_MESSAGES,
        ADD_REACTIONS, MENTION_ALL, CREATE_INVITES
    ]
    
    # группировка для UI
    GROUPS = {
        "chat_management": {
            "name": "Управление чатом",
            "permissions": [CHANGE_INFO, DELETE_SPACE]
        },
        "member_management": {
            "name": "Управление участниками",
            "permissions": [ADD_MEMBERS, BAN_MEMBERS, KICK_MEMBERS, RESTRICT_MEMBERS, PROMOTE_MEMBERS]
        },
        "messaging": {
            "name": "Отправка сообщений",
            "permissions": [SEND_MESSAGES, SEND_MEDIA, SEND_STICKERS, SEND_FILES]
        },
        "message_management": {
            "name": "Управление сообщениями",
            "permissions": [EDIT_OWN_MESSAGES, DELETE_OWN_MESSAGES, DELETE_ANY_MESSAGES, PIN_MESSAGES]
        },
        "additional": {
            "name": "Дополнительно",
            "permissions": [ADD_REACTIONS, MENTION_ALL, CREATE_INVITES]
        }
    }


class RolePreset:
    """Предустановленные роли"""
    
    OWNER = {
        "name": "Владелец",
        "permissions": Permission.ALL,
        "color": "#FF0000",
        "priority": 100,
        "is_system": True  # владельца нельзя удалить или изменить
    }
    
    ADMIN = {
        "name": "Администратор",
        "permissions": [
            Permission.CHANGE_INFO,
            Permission.ADD_MEMBERS,
            Permission.BAN_MEMBERS,
            Permission.KICK_MEMBERS,
            Permission.RESTRICT_MEMBERS,
            Permission.SEND_MESSAGES,
            Permission.SEND_MEDIA,
            Permission.SEND_STICKERS,
            Permission.SEND_FILES,
            Permission.EDIT_OWN_MESSAGES,
            Permission.DELETE_OWN_MESSAGES,
            Permission.DELETE_ANY_MESSAGES,
            Permission.PIN_MESSAGES,
            Permission.ADD_REACTIONS,
            Permission.CREATE_INVITES,
        ],
        "color": "#FFA500",
        "priority": 80,
        "is_system": False
    }
    
    MODERATOR = {
        "name": "Модератор",
        "permissions": [
            Permission.KICK_MEMBERS,
            Permission.RESTRICT_MEMBERS,
            Permission.SEND_MESSAGES,
            Permission.SEND_MEDIA,
            Permission.SEND_STICKERS,
            Permission.SEND_FILES,
            Permission.EDIT_OWN_MESSAGES,
            Permission.DELETE_OWN_MESSAGES,
            Permission.DELETE_ANY_MESSAGES,
            Permission.PIN_MESSAGES,
            Permission.ADD_REACTIONS,
        ],
        "color": "#00FF00",
        "priority": 60,
        "is_system": False
    }
    
    MEMBER = {
        "name": "Участник",
        "permissions": [
            Permission.SEND_MESSAGES,
            Permission.SEND_MEDIA,
            Permission.SEND_STICKERS,
            Permission.SEND_FILES,
            Permission.EDIT_OWN_MESSAGES,
            Permission.DELETE_OWN_MESSAGES,
            Permission.ADD_REACTIONS,
        ],
        "color": "#0000FF",
        "priority": 10,
        "is_system": True  # назначаемая по умолчанию роль
    }
    
    RESTRICTED = {
        "name": "Ограниченный",
        "permissions": [
        ],
        "color": "#808080",
        "priority": 5,
        "is_system": False
    }

# иерархия ролей (чем больше число, тем выше роль)
class RoleHierarchy:
    LEVELS = {
        "Ограниченный": 0,
        "Участник": 1,
        "Модератор": 2,
        "Владелец": 3
    }

    @staticmethod
    def get_level(role_name: str) -> int:
        """Получить уровень роли"""
        return RoleHierarchy.LEVELS.get(role_name, 0)

    @staticmethod
    def can_moderate(moderator_role: str, target_role: str) -> bool:
        """Проверить, может ли moderator управлять target"""
        moderator_level = RoleHierarchy.get_level(moderator_role)
        target_level = RoleHierarchy.get_level(target_role)
        return moderator_level > target_level


def has_permission(user_permissions: list, required_permission: str) -> bool:
    """Проверить наличие разрешения у пользователя"""
    return required_permission in user_permissions

def get_permission_info(permission: str) -> dict:
    """Получить информацию о разрешении для UI"""
    info_map = {
        Permission.CHANGE_INFO: {
            "name": "Изменять информацию",
            "description": "Может менять название и описание комнаты"
        },
        Permission.DELETE_SPACE: {
            "name": "Удалять комнату",
            "description": "Может полностью удалить комнату"
        },
        Permission.ADD_MEMBERS: {
            "name": "Добавлять участников",
            "description": "Может приглашать новых участников"
        },
        Permission.BAN_MEMBERS: {
            "name": "Банить участников",
            "description": "Может банить и разбанивать участников"
        },
        Permission.KICK_MEMBERS: {
            "name": "Удалять участников",
            "description": "Может удалять участников из комнаты"
        },
        Permission.RESTRICT_MEMBERS: {
            "name": "Ограничивать участников",
            "description": "Может ограничивать права других участников"
        },
        Permission.PROMOTE_MEMBERS: {
            "name": "Назначать администраторов",
            "description": "Может назначать других администраторов"
        },
        Permission.SEND_MESSAGES: {
            "name": "Отправлять сообщения",
            "description": "Может отправлять текстовые сообщения"
        },
        Permission.SEND_MEDIA: {
            "name": "Отправлять медиа",
            "description": "Может отправлять фото, видео и аудио"
        },
        Permission.SEND_STICKERS: {
            "name": "Отправлять стикеры",
            "description": "Может отправлять стикеры и GIF"
        },
        Permission.SEND_FILES: {
            "name": "Отправлять файлы",
            "description": "Может отправлять документы и другие файлы"
        },
        Permission.EDIT_OWN_MESSAGES: {
            "name": "Редактировать свои сообщения",
            "description": "Может редактировать отправленные сообщения"
        },
        Permission.DELETE_OWN_MESSAGES: {
            "name": "Удалять свои сообщения",
            "description": "Может удалять свои сообщения"
        },
        Permission.DELETE_ANY_MESSAGES: {
            "name": "Удалять любые сообщения",
            "description": "Может удалять сообщения других участников"
        },
        Permission.PIN_MESSAGES: {
            "name": "Закреплять сообщения",
            "description": "Может закреплять важные сообщения"
        },
        Permission.ADD_REACTIONS: {
            "name": "Ставить реакции",
            "description": "Может ставить реакции на сообщения"
        },
        Permission.MENTION_ALL: {
            "name": "Упоминать всех",
            "description": "Может использовать @everyone"
        },
        Permission.CREATE_INVITES: {
            "name": "Создавать приглашения",
            "description": "Может создавать пригласительные ссылки"
        },
    }
    return info_map.get(permission, {"name": permission, "description": ""})
