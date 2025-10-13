import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import UserRole, Role


async def check_permissions(
    db: AsyncSession,
    user_id: int,
    space_id: int,
    required_permission: str,
    space_admin_id: int
) -> bool:
    """Проверить, есть ли у пользователя нужное разрешение в пространстве.

    Возвращает True, если пользователь админ пространства или имеет права через роль.
    """
    # Админ пространства имеет все права
    if user_id == space_admin_id:
        return True

    # Проверяем права роли пользователя
    result = await db.execute(
        select(UserRole).join(Role).filter(
            UserRole.user_id == user_id,
            Role.space_id == space_id
        )
    )
    user_role = result.scalar_one_or_none()

    if not user_role:
        return False

    permissions = user_role.role.permissions

    # Обрабатываем JSON строку
    if isinstance(permissions, str):
        permissions = json.loads(permissions)

    permissions = permissions or []

    # Проверяем конкретное право или админ-право
    return required_permission in permissions or "admin" in permissions
