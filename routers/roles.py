import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, DatabaseError

from models import Role, Space, User, UserRole
from schemas import RoleCreate, RoleOut
from utils.database import get_async_db
from utils.dependencies import get_current_user
from utils.permissions import check_permissions


# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

router = APIRouter(prefix="/spaces", tags=["roles"])


@router.post("/{space_id}/roles", response_model=RoleOut)
async def create_role(
    space_id: int,
    role: RoleCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_db)
):
    """Create a new role in a space (requires assign_role permission)."""
    try:
        logger.info(
            f"User {current_user.id} creating role '{role.name}' in space "
            f"{space_id}"
        )

        # Verify space exists
        result = await db.execute(
            select(Space).filter(Space.id == space_id)
        )
        space = result.scalar_one_or_none()
        if not space:
            logger.warning(f"Space {space_id} not found")
            raise HTTPException(
                status_code=404,
                detail="Пространство не найдено"
            )

        # Check permissions
        has_permission = await check_permissions(
            db,
            current_user.id,
            space_id,
            "assign_role",
            space.admin_id
        )
        if not has_permission:
            logger.warning(
                f"User {current_user.id} lacks assign_role permission in "
                f"space {space_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="У вас нет прав на создание ролей"
            )

        # Create role
        new_role = Role(
            space_id=space_id,
            name=role.name,
            permissions=role.permissions,
            color=role.color
        )
        db.add(new_role)
        await db.commit()
        await db.refresh(new_role)

        logger.info(
            f"Role {new_role.id} '{role.name}' created in space "
            f"{space_id} by user {current_user.id}"
        )
        return new_role

    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(
            f"Integrity error creating role: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=400,
            detail="Ошибка целостности данных при создании роли"
        )
    except DatabaseError as e:
        await db.rollback()
        logger.error(
            f"Database error creating role: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Ошибка базы данных"
        )
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Unexpected error creating role: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера"
        )


@router.post("/{space_id}/assign-role/{user_id}/{role_id}")
async def assign_role(
    space_id: int,
    user_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_db)
):
    """Assign a role to user in space (requires assign_role permission)."""
    try:
        logger.info(
            f"User {current_user.id} assigning role {role_id} to user "
            f"{user_id} in space {space_id}"
        )

        # Verify space exists
        result = await db.execute(
            select(Space).filter(Space.id == space_id)
        )
        space = result.scalar_one_or_none()
        if not space:
            logger.warning(f"Space {space_id} not found")
            raise HTTPException(
                status_code=404,
                detail="Пространство не найдено"
            )

        # Check permissions
        has_permission = await check_permissions(
            db,
            current_user.id,
            space_id,
            "assign_role",
            space.admin_id
        )
        if not has_permission:
            logger.warning(
                f"User {current_user.id} lacks assign_role permission in "
                f"space {space_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="У вас нет прав на назначение ролей"
            )

        # Verify role exists and belongs to this space
        result = await db.execute(
            select(Role).filter(
                Role.id == role_id,
                Role.space_id == space_id
            )
        )
        role = result.scalar_one_or_none()
        if not role:
            logger.warning(
                f"Role {role_id} not found in space {space_id}"
            )
            raise HTTPException(
                status_code=404,
                detail="Роль не найдена"
            )

        # Check if role already assigned
        result = await db.execute(
            select(UserRole).filter(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            logger.warning(
                f"Role {role_id} already assigned to user {user_id}"
            )
            raise HTTPException(
                status_code=400,
                detail="Роль уже назначена"
            )

        # Assign role
        new_user_role = UserRole(user_id=user_id, role_id=role_id)
        db.add(new_user_role)
        await db.commit()

        logger.info(
            f"Role {role_id} assigned to user {user_id} in space "
            f"{space_id} by {current_user.id}"
        )
        return {"message": "Роль успешно назначена"}

    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(
            f"Integrity error assigning role: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=400,
            detail="Ошибка целостности данных при назначении роли"
        )
    except DatabaseError as e:
        await db.rollback()
        logger.error(
            f"Database error assigning role: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Ошибка базы данных"
        )
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Unexpected error assigning role: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера"
        )
