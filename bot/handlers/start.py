"""Start and main menu handlers — EN only."""
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from loguru import logger

from bot.database import get_session_factory
from bot.keyboards.main_kb import main_menu_kb
from bot.services.user_service import get_or_create_user
from bot.services.product_service import get_or_create_product

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command — register user and show main menu."""
    user = message.from_user
    if not user:
        return

    factory = get_session_factory()
    async with factory() as session:
        db_user, created = await get_or_create_user(session, user)
        product = await get_or_create_product(session)
        await session.commit()

    logger.info(
        "/start | user_id={} username={} new_user={}",
        user.id, user.username, created,
    )

    await message.answer(
        text=product.get_welcome_text("en"),
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery) -> None:
    """Return to main menu from any screen."""
    user = callback.from_user
    logger.debug("Back to main menu | user_id={}", user.id)
    await callback.answer()

    factory = get_session_factory()
    async with factory() as session:
        product = await get_or_create_product(session)

    await callback.message.edit_text(  # type: ignore[union-attr]
        text=product.get_welcome_text("en"),
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
