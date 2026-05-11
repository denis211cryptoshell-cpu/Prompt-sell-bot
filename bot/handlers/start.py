"""Start and main menu handlers."""
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from loguru import logger

from bot.database import get_session_factory
from bot.keyboards.main_kb import main_menu_kb
from bot.services.user_service import get_or_create_user, get_user_lang
from bot.services.product_service import get_or_create_product

router = Router(name="start")


async def _show_main_menu(message: Message, edit: bool = False, welcome: str = "", lang: str = "ru") -> None:
    """Show main menu — either send new or edit existing message."""
    if edit and hasattr(message, "edit_text"):
        await message.edit_text(
            text=welcome,
            reply_markup=main_menu_kb(lang),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            text=welcome,
            reply_markup=main_menu_kb(lang),
            parse_mode="HTML",
        )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command — register user and show main menu."""
    user = message.from_user
    if not user:
        return

    factory = get_session_factory()
    async with factory() as session:
        db_user, created = await get_or_create_user(session, user)
        lang = db_user.language
        product = await get_or_create_product(session)
        await session.commit()

    logger.info(
        "/start | user_id={} username={} new_user={} lang={}",
        user.id, user.username, created, lang,
    )

    await _show_main_menu(message, edit=False, welcome=product.get_welcome_text(lang), lang=lang)


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery) -> None:
    """Return to main menu from any screen."""
    user = callback.from_user
    logger.debug("Back to main menu | user_id={}", user.id)
    await callback.answer()

    factory = get_session_factory()
    async with factory() as session:
        lang = await get_user_lang(session, user.id)
        product = await get_or_create_product(session)

    await _show_main_menu(
        callback.message,  # type: ignore[arg-type]
        edit=True,
        welcome=product.get_welcome_text(lang),
        lang=lang,
    )
