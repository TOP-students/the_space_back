import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError, DatabaseError

from models import Ban, Chat, ChatParticipant, Space, User
from schemas import BanCreate, SpaceCreate, SpaceOut, UserOut
from utils.database import get_async_db
from utils.dependencies import get_current_user
from utils.permissions import check_permissions


# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

router = APIRouter(prefix="/spaces", tags=["spaces"])


@router.post("", response_model=SpaceOut)
async def create_space(
    space: SpaceCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_db)
):
    """Create a new space with associated chat and participant."""
    try:
        logger.info(
            f"User {current_user.id} creating space: {space.name}"
        )

        # Create space first
        new_space = Space(
            name=space.name,
            description=space.description,
            admin_id=current_user.id,
            background_url=space.background_url
        )
        db.add(new_space)
        await db.flush()  # Get space ID before creating chat

        # Create associated group chat
        chat = Chat(type="group", space_id=new_space.id)
        db.add(chat)
        await db.flush()  # Get chat ID for participant

        # Add creator as first participant
        participant = ChatParticipant(
            chat_id=chat.id,
            user_id=current_user.id,
            is_active=True
        )
        db.add(participant)

        # Link chat back to space
        new_space.chat_id = chat.id

        await db.commit()
        await db.refresh(new_space)

        logger.info(
            f"Space {new_space.id} created successfully by user "
            f"{current_user.id}"
        )
        return new_space

    except IntegrityError as e:
        await db.rollback()
        logger.error(
            f"Integrity error creating space: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=400,
            detail="Ошибка целостности данных при создании пространства"
        )
    except DatabaseError as e:
        await db.rollback()
        logger.error(
            f"Database error creating space: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Ошибка базы данных"
        )
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Unexpected error creating space: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера"
        )


@router.post("/{space_id}/join")
async def join_space(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_db)
):
    """Join a space if user is not banned."""
    try:
        logger.info(
            f"User {current_user.id} attempting to join space {space_id}"
        )

        # Check if space exists
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

        # Check for active bans
        ban_query = select(Ban).filter(
            Ban.user_id == current_user.id,
            Ban.space_id == space_id,
            or_(
                Ban.until > datetime.now(timezone.utc),
                Ban.until.is_(None)
            )
        )
        result = await db.execute(ban_query)
        active_ban = result.scalar_one_or_none()

        if active_ban:
            logger.warning(
                f"User {current_user.id} is banned from space {space_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Вы забанены в этом пространстве"
            )

        # Get space chat
        result = await db.execute(
            select(Chat).filter(Chat.space_id == space_id)
        )
        chat = result.scalar_one_or_none()
        if not chat:
            logger.error(
                f"Chat not found for space {space_id}"
            )
            raise HTTPException(
                status_code=404,
                detail="Чат для пространства не найден"
            )

        # Check if already a participant
        result = await db.execute(
            select(ChatParticipant).filter(
                ChatParticipant.chat_id == chat.id,
                ChatParticipant.user_id == current_user.id
            )
        )
        existing = result.scalar_one_or_none()

        if existing and existing.is_active:
            logger.info(
                f"User {current_user.id} already in space {space_id}"
            )
            raise HTTPException(
                status_code=400,
                detail="Вы уже участник"
            )

        # Reactivate or create participant
        if existing:
            existing.is_active = True
            logger.info(
                f"Reactivated participant {current_user.id} in space "
                f"{space_id}"
            )
        else:
            new_participant = ChatParticipant(
                chat_id=chat.id,
                user_id=current_user.id,
                is_active=True
            )
            db.add(new_participant)
            logger.info(
                f"Added new participant {current_user.id} to space "
                f"{space_id}"
            )

        await db.commit()
        return {"message": "Успешно присоединены к пространству"}

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except DatabaseError as e:
        await db.rollback()
        logger.error(
            f"Database error joining space: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Ошибка базы данных"
        )
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Unexpected error joining space: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера"
        )


@router.get("/{space_id}/participants", response_model=List[UserOut])
async def get_participants(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_db)
):
    """Get list of active participants in a space."""
    try:
        logger.info(
            f"User {current_user.id} fetching participants for space "
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

        # Get space chat
        result = await db.execute(
            select(Chat).filter(Chat.space_id == space_id)
        )
        chat = result.scalar_one_or_none()
        if not chat:
            logger.warning(f"No chat found for space {space_id}")
            return []

        # Fetch active participants
        query = select(User).join(ChatParticipant).filter(
            ChatParticipant.chat_id == chat.id,
            ChatParticipant.is_active.is_(True)
        )
        result = await db.execute(query)
        participants = result.scalars().all()

        logger.info(
            f"Found {len(participants)} participants in space {space_id}"
        )
        return participants

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(
            f"Database error fetching participants: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Ошибка базы данных"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error fetching participants: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера"
        )


@router.delete("/{space_id}/kick/{user_id}")
async def kick_user(
    space_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_db)
):
    """Kick user from space (requires kick permission)."""
    try:
        logger.info(
            f"User {current_user.id} attempting to kick user {user_id} "
            f"from space {space_id}"
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
            "kick",
            space.admin_id
        )
        if not has_permission:
            logger.warning(
                f"User {current_user.id} lacks kick permission in space "
                f"{space_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="У вас нет прав на кик"
            )

        # Get space chat
        result = await db.execute(
            select(Chat).filter(Chat.space_id == space_id)
        )
        chat = result.scalar_one_or_none()
        if not chat:
            logger.error(f"Chat not found for space {space_id}")
            raise HTTPException(
                status_code=404,
                detail="Чат не найден"
            )

        # Find participant
        result = await db.execute(
            select(ChatParticipant).filter(
                ChatParticipant.chat_id == chat.id,
                ChatParticipant.user_id == user_id
            )
        )
        participant = result.scalar_one_or_none()
        if not participant:
            logger.warning(
                f"User {user_id} not found in space {space_id}"
            )
            raise HTTPException(
                status_code=404,
                detail="Пользователь не найден в пространстве"
            )

        # Deactivate participant
        participant.is_active = False
        await db.commit()

        logger.info(
            f"User {user_id} kicked from space {space_id} by "
            f"{current_user.id}"
        )
        return {"message": "Пользователь успешно кикнут"}

    except HTTPException:
        raise
    except DatabaseError as e:
        await db.rollback()
        logger.error(
            f"Database error kicking user: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Ошибка базы данных"
        )
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Unexpected error kicking user: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера"
        )


@router.post("/{space_id}/ban/{user_id}")
async def ban_user(
    space_id: int,
    user_id: int,
    ban_data: BanCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_db)
):
    """Ban user from space (requires ban permission)."""
    try:
        logger.info(
            f"User {current_user.id} attempting to ban user {user_id} "
            f"from space {space_id}"
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
            "ban",
            space.admin_id
        )
        if not has_permission:
            logger.warning(
                f"User {current_user.id} lacks ban permission in space "
                f"{space_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="У вас нет прав на бан"
            )

        # Create ban record
        new_ban = Ban(
            user_id=user_id,
            banned_by=current_user.id,
            space_id=space_id,
            reason=ban_data.reason,
            until=ban_data.until
        )
        db.add(new_ban)

        # Deactivate participant if exists
        result = await db.execute(
            select(Chat).filter(Chat.space_id == space_id)
        )
        chat = result.scalar_one_or_none()

        if chat:
            result = await db.execute(
                select(ChatParticipant).filter(
                    ChatParticipant.chat_id == chat.id,
                    ChatParticipant.user_id == user_id
                )
            )
            participant = result.scalar_one_or_none()
            if participant:
                participant.is_active = False

        await db.commit()

        logger.info(
            f"User {user_id} banned from space {space_id} by "
            f"{current_user.id}"
        )
        return {"message": "Пользователь успешно забанен"}

    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(
            f"Integrity error banning user: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=400,
            detail="Ошибка целостности данных при бане"
        )
    except DatabaseError as e:
        await db.rollback()
        logger.error(
            f"Database error banning user: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Ошибка базы данных"
        )
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Unexpected error banning user: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера"
        )
