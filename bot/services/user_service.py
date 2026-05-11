"""User CRUD service."""
from typing import Optional

from aiogram.types import User as TelegramUser
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.user import User
from bot.i18n import detect_lang


async def get_or_create_user(session: AsyncSession, tg_user: TelegramUser) -> tuple[User, bool]:
    """
    Get existing user or create a new one.
    Returns (user, created) tuple.
    Auto-detects language on first registration.
    """
    result = await session.execute(select(User).where(User.id == tg_user.id))
    user = result.scalar_one_or_none()

    if user:
        # Update name fields in case they changed
        changed = False
        if user.first_name != tg_user.first_name:
            user.first_name = tg_user.first_name
            changed = True
        if user.last_name != tg_user.last_name:
            user.last_name = tg_user.last_name
            changed = True
        if user.username != tg_user.username:
            user.username = tg_user.username
            changed = True
        if changed:
            await session.flush()
            logger.debug("User profile updated | user_id={}", tg_user.id)
        return user, False

    # Auto-detect language from Telegram profile
    lang = detect_lang(tg_user.language_code)

    user = User(
        id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
        language=lang,
    )
    session.add(user)
    await session.flush()
    logger.info(
        "New user registered | user_id={} username={} name={!r} lang={}",
        tg_user.id, tg_user.username, tg_user.full_name, lang,
    )
    return user, True


async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    """Fetch user by Telegram ID."""
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_lang(session: AsyncSession, user_id: int) -> str:
    """Get user's language preference. Returns 'ru' if user not found."""
    result = await session.execute(select(User.language).where(User.id == user_id))
    lang = result.scalar_one_or_none()
    return lang or "ru"


async def set_user_lang(session: AsyncSession, user_id: int, lang: str) -> None:
    """Update user's language preference."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.language = lang
        await session.flush()
        logger.info("Language updated | user_id={} lang={}", user_id, lang)
    else:
        logger.warning("set_user_lang: user not found | user_id={}", user_id)
