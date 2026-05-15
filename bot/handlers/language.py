"""Language selection handler."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from bot.database import get_session_factory
from bot.i18n import t, SUPPORTED_LANGS
from bot.services.user_service import get_user_lang, set_user_lang

router = Router(name="language")


def language_kb(current_lang: str = "ru") -> InlineKeyboardMarkup:
    """Language selection keyboard."""
    builder = InlineKeyboardBuilder()
    ru_mark = "✅ " if current_lang == "ru" else ""
    en_mark = "✅ " if current_lang == "en" else ""
    builder.button(text=f"{ru_mark}🇷🇺 Русский", callback_data="lang:set:ru")
    builder.button(text=f"{en_mark}🇬🇧 English", callback_data="lang:set:en")
    builder.button(text="◀️ Назад / Back", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data.in_({"menu:language", "lang:select"}))
async def cb_language_menu(callback: CallbackQuery) -> None:
    """Show language selection screen."""
    user_id = callback.from_user.id
    await callback.answer()

    factory = get_session_factory()
    async with factory() as session:
        lang = await get_user_lang(session, user_id)

    logger.debug("Language menu | user_id={} current_lang={}", user_id, lang)

    text = (
        "🌐 <b>Выбор языка / Language selection</b>\n\n"
        "Выберите язык интерфейса:\n"
        "Choose interface language:"
    )
    await callback.message.edit_text(  # type: ignore[union-attr]
        text=text,
        reply_markup=language_kb(lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("lang:set:"))
async def cb_set_language(callback: CallbackQuery) -> None:
    """Handle language selection."""
    user_id = callback.from_user.id
    new_lang = callback.data.split(":")[-1]  # type: ignore[union-attr]

    if new_lang not in SUPPORTED_LANGS:
        await callback.answer("❌ Unknown language", show_alert=True)
        return

    factory = get_session_factory()
    async with factory() as session:
        await set_user_lang(session, user_id, new_lang)
        await session.commit()

    logger.info("Language set | user_id={} lang={}", user_id, new_lang)

    confirmation = t("lang_set", new_lang)
    await callback.answer(confirmation, show_alert=False)

    # Refresh language screen with new checkmark
    text = (
        "🌐 <b>Выбор языка / Language selection</b>\n\n"
        "Выберите язык интерфейса:\n"
        "Choose interface language:"
    )
    await callback.message.edit_text(  # type: ignore[union-attr]
        text=text,
        reply_markup=language_kb(new_lang),
        parse_mode="HTML",
    )
