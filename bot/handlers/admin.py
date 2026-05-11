"""Admin panel handlers with FSM for editing product fields and scene customization."""
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy import func, select

from bot.config import settings
from bot.database import get_session_factory
from bot.keyboards.admin_kb import (
    admin_main_kb,
    admin_back_kb,
    admin_cancel_kb,
    admin_customize_kb,
    admin_back_customize_kb,
    admin_cancel_customize_kb,
    admin_en_customize_kb,
    admin_cancel_en_kb,
)
from bot.keyboards.main_kb import product_kb
from bot.models.purchase import Purchase
from bot.models.user import User
from bot.services.product_service import get_or_create_product, update_product_field
from bot.services.cache import invalidate_product_cache
from bot.services.currency import get_usd_rate, rub_to_usd, format_usd
from bot.states.admin_states import AdminStates
from bot.utils.text import (
    admin_panel_text,
    admin_stats_text,
    product_card_text,
    escape_md,
)

router = Router(name="admin")


async def _admin_text(product) -> str:
    """Build admin panel text with live USD price."""
    usd_val = await rub_to_usd(product.price)
    return admin_panel_text(
        product.name, product.price, bool(product.pdf_file_id),
        price_usd=format_usd(usd_val),
    )


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids_list


# ═══════════════════════════════════════════════════════════════════════════════
# /admin command
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    user = message.from_user
    if not user or not _is_admin(user.id):
        logger.warning("Unauthorized /admin attempt | user_id={}", user.id if user else "?")
        await message.answer("⛔ У вас нет доступа к панели администратора.")
        return

    logger.info("Admin panel opened | user_id={}", user.id)
    factory = get_session_factory()
    async with factory() as session:
        product = await get_or_create_product(session)

    await message.answer(
        text=await _admin_text(product),
        reply_markup=admin_main_kb(product),
        parse_mode="MarkdownV2",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Admin menu (callback)
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:menu")
async def cb_admin_menu(callback: CallbackQuery, state: FSMContext) -> None:
    user = callback.from_user
    if not _is_admin(user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.answer()

    factory = get_session_factory()
    async with factory() as session:
        product = await get_or_create_product(session)

    await callback.message.edit_text(  # type: ignore[union-attr]
        text=await _admin_text(product),
        reply_markup=admin_main_kb(product),
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "admin:close")
async def cb_admin_close(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Панель закрыта")
    await callback.message.delete()  # type: ignore[union-attr]


# ═══════════════════════════════════════════════════════════════════════════════
# Statistics
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(callback: CallbackQuery) -> None:
    user = callback.from_user
    if not _is_admin(user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.answer()

    factory = get_session_factory()
    async with factory() as session:
        total_users = (await session.execute(select(func.count(User.id)))).scalar_one()
        total_purchases = (
            await session.execute(
                select(func.count(Purchase.id)).where(Purchase.status == "completed")
            )
        ).scalar_one()
        total_revenue = (
            await session.execute(
                select(func.coalesce(func.sum(Purchase.amount), 0)).where(
                    Purchase.status == "completed"
                )
            )
        ).scalar_one()

    logger.info(
        "Admin stats | user_id={} users={} purchases={} revenue={}",
        user.id, total_users, total_purchases, total_revenue,
    )
    await callback.message.edit_text(  # type: ignore[union-attr]
        text=admin_stats_text(total_users, total_purchases, total_revenue),
        reply_markup=admin_back_kb(),
        parse_mode="MarkdownV2",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Product preview
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:preview")
async def cb_admin_preview(callback: CallbackQuery) -> None:
    user = callback.from_user
    if not _is_admin(user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.answer()

    factory = get_session_factory()
    async with factory() as session:
        product = await get_or_create_product(session)

    usd_val = await rub_to_usd(product.price)
    text = product_card_text(
        name=product.name,
        description=product.description,
        price=product.price,
        has_pdf=bool(product.pdf_file_id),
        price_usd=format_usd(usd_val),
    )
    await callback.message.edit_text(  # type: ignore[union-attr]
        text=f"👁 <b>Предпросмотр продукта:</b>\n\n{text}",
        reply_markup=admin_back_kb(),
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 🎨 CUSTOMIZATION SUBMENU
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:customize:menu")
async def cb_customize_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Open customization submenu."""
    user = callback.from_user
    if not _is_admin(user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.answer()

    factory = get_session_factory()
    async with factory() as session:
        product = await get_or_create_product(session)

    text = (
        f"🎨 <b>Кастомизация бота</b>\n\n"
        f"Выберите сцену для редактирования.\n\n"
        f"<b>Текущие тексты:</b>\n"
        f'━━━━━━━━━━━━━━━━━━━━\n'
        f"🏠 Приветствие: {'<i>стандартное</i>' if not product.welcome_text else '<b>изменено ✅</b>'}\n"
        f"🎉 Успешная оплата: {'<i>стандартный</i>' if not product.success_text else '<b>изменено ✅</b>'}\n"
        f"♻️ «Уже куплено»: {'<i>стандартный</i>' if not product.already_purchased_text else '<b>изменено ✅</b>'}\n"
        f"📎 Подпись к файлу: {'<i>стандартная</i>' if not product.file_caption else f'<b>{product.file_caption[:30]}</b>'}\n"
        f'━━━━━━━━━━━━━━━━━━━━\n\n'
        f"💡 Подсказка: в текстах можно использовать <code>{{name}}</code> — будет заменено на название продукта."
    )
    await callback.message.edit_text(  # type: ignore[union-attr]
        text=text,
        reply_markup=admin_customize_kb(),
        parse_mode="HTML",
    )


# ── Customization field entry ──────────────────────────────────────────────────

_CUSTOMIZE_CONFIG: dict[str, tuple[AdminStates, str, str]] = {
    "welcome_text": (
        AdminStates.waiting_for_welcome_text,
        "🏠 <b>Приветствие (/start)</b>",
        (
            "Введите новый текст приветствия.\n\n"
            "Поддерживается HTML-разметка: <code>&lt;b&gt;жирный&lt;/b&gt;</code>, "
            "<code>&lt;i&gt;курсив&lt;/i&gt;</code>.\n\n"
            "Используйте <code>{name}</code> для подстановки названия продукта.\n\n"
            "Или отправьте <code>сброс</code> для возврата к стандартному тексту."
        ),
    ),
    "success_text": (
        AdminStates.waiting_for_success_text,
        "🎉 <b>Текст после успешной оплаты</b>",
        (
            "Введите текст, который увидит пользователь после оплаты.\n\n"
            "Поддерживается HTML. Используйте <code>{name}</code> для названия продукта.\n\n"
            "Отправьте <code>сброс</code> для возврата к стандартному тексту."
        ),
    ),
    "already_purchased_text": (
        AdminStates.waiting_for_already_purchased_text,
        "♻️ <b>Текст «Вы уже купили»</b>",
        (
            "Введите текст для пользователей, которые уже приобрели продукт.\n\n"
            "Поддерживается HTML. Используйте <code>{name}</code> для названия продукта.\n\n"
            "Отправьте <code>сброс</code> для возврата к стандартному тексту."
        ),
    ),
    "file_caption": (
        AdminStates.waiting_for_file_caption,
        "📎 <b>Подпись к файлу</b>",
        (
            "Введите подпись, которая будет отображаться под отправляемым файлом.\n\n"
            "Используйте <code>{name}</code> для названия продукта.\n"
            "Пример: <code>📄 Ваш {name} — сохраните!</code>\n\n"
            "Отправьте <code>сброс</code> для возврата к стандартному."
        ),
    ),
    "confirm_footer_text": (
        AdminStates.waiting_for_confirm_footer_text,
        "📜 <b>Подвал экрана подтверждения покупки</b>",
        (
            "Введите текст, который будет показан внизу экрана подтверждения — "
            "перед кнопкой оплаты.\n\n"
            "Здесь обычно размещают:\n"
            "• Ссылку на оферту (HTML: <code>&lt;a href=\"URL\"&gt;текст&lt;/a&gt;</code>)\n"
            "• ИНН организации\n"
            "• Email для связи\n\n"
            "Поддерживается HTML. Пример:\n"
            "<code>Нажимая кнопку, вы принимаете условия "
            "&lt;a href=\"https://example.com/oferta\"&gt;оферты&lt;/a&gt;.\n"
            "ИНН: 1234567890\nEmail: info@company.ru</code>\n\n"
            "Отправьте <code>сброс</code> для возврата к стандартному."
        ),
    ),
}


@router.callback_query(
    F.data.startswith("admin:customize:")
    & ~F.data.endswith(":menu")
    & (F.data != "admin:customize:en_menu")
)
async def cb_customize_field(callback: CallbackQuery, state: FSMContext) -> None:
    """Enter FSM state for customizing a scene text."""
    user = callback.from_user
    if not _is_admin(user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    field = callback.data.split("admin:customize:")[1]
    config = _CUSTOMIZE_CONFIG.get(field)
    if not config:
        await callback.answer("Неизвестное поле", show_alert=True)
        return

    fsm_state, title, prompt = config
    await state.set_state(fsm_state)
    await state.update_data(field=field)
    await callback.answer()

    logger.debug("Admin customize field | user_id={} field={}", user.id, field)

    # Show current value
    factory = get_session_factory()
    async with factory() as session:
        product = await get_or_create_product(session)
    current = getattr(product, field, None)
    current_block = f"\n\n<b>Текущий текст:</b>\n<i>{current[:200] if current else 'стандартный'}</i>" if True else ""

    await callback.message.edit_text(  # type: ignore[union-attr]
        text=f"{title}\n\n{prompt}{current_block}",
        reply_markup=admin_cancel_customize_kb(),
        parse_mode="HTML",
    )


# ── Receive customization values ───────────────────────────────────────────────

@router.message(AdminStates.waiting_for_welcome_text)
async def fsm_receive_welcome_text(message: Message, state: FSMContext) -> None:
    await _save_custom_text(message, state, "welcome_text")


@router.message(AdminStates.waiting_for_success_text)
async def fsm_receive_success_text(message: Message, state: FSMContext) -> None:
    await _save_custom_text(message, state, "success_text")


@router.message(AdminStates.waiting_for_already_purchased_text)
async def fsm_receive_already_purchased_text(message: Message, state: FSMContext) -> None:
    await _save_custom_text(message, state, "already_purchased_text")


@router.message(AdminStates.waiting_for_file_caption)
async def fsm_receive_file_caption(message: Message, state: FSMContext) -> None:
    await _save_custom_text(message, state, "file_caption")


@router.message(AdminStates.waiting_for_confirm_footer_text)
async def fsm_receive_confirm_footer_text(message: Message, state: FSMContext) -> None:
    await _save_custom_text(message, state, "confirm_footer_text")


async def _save_custom_text(message: Message, state: FSMContext, field: str) -> None:
    """Save custom text field. 'сброс' resets to default (None)."""
    user = message.from_user
    raw = (message.text or "").strip()
    await state.clear()

    value = None if raw.lower() in ("сброс", "reset", "/reset") else raw

    factory = get_session_factory()
    async with factory() as session:
        product = await get_or_create_product(session)
        updated = await update_product_field(session, product.id, field, value)
        await session.commit()

    if not updated:
        await message.answer("❌ Ошибка при сохранении. Попробуйте снова.")
        return

    action = "сброшен до стандартного" if value is None else "сохранён"
    logger.info(
        "Admin customized field | user_id={} field={} action={}",
        user.id, field, action,
    )

    await message.answer(
        f"✅ <b>Текст {action}!</b>",
        parse_mode="HTML",
    )
    # Return to customization menu
    await message.answer(
        text=(
            "🎨 <b>Кастомизация</b>\n\nВыберите следующую сцену или вернитесь в меню:"
        ),
        reply_markup=admin_customize_kb(),
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Core product fields (name, price, description, buttons)
# ═══════════════════════════════════════════════════════════════════════════════

_FIELD_CONFIG: dict[str, tuple[str, AdminStates, str]] = {
    "name": (
        "название",
        AdminStates.waiting_for_name,
        "Введите новое название продукта:",
    ),
    "price": (
        "цену",
        AdminStates.waiting_for_price,
        "Введите новую цену в рублях (только число):",
    ),
    "description": (
        "описание",
        AdminStates.waiting_for_description,
        "Введите новое описание продукта:",
    ),
    "buy_button_text": (
        "текст кнопки покупки",
        AdminStates.waiting_for_buy_button_text,
        "Введите текст кнопки покупки.\nИспользуйте {price} для подстановки цены:",
    ),
    "confirm_button_text": (
        "текст кнопки подтверждения",
        AdminStates.waiting_for_confirm_button_text,
        "Введите текст кнопки подтверждения оплаты:",
    ),
    "price_usd": (
        "цену в долларах",
        AdminStates.waiting_for_price_usd,
        "💵 Введите цену в долларах (например: 3.99 или 5):\n\nБудет автоматически конвертирована в рубли по курсу ЦБ.",
    ),
}


@router.callback_query(F.data.startswith("admin:edit:"))
async def cb_admin_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    user = callback.from_user
    if not _is_admin(user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    field = callback.data.split("admin:edit:")[1]
    config = _FIELD_CONFIG.get(field)
    if not config:
        await callback.answer("Неизвестное поле", show_alert=True)
        return

    _, fsm_state, prompt = config
    await state.set_state(fsm_state)
    await state.update_data(field=field)
    await callback.answer()

    logger.debug("Admin edit field | user_id={} field={}", user.id, field)

    await callback.message.edit_text(  # type: ignore[union-attr]
        text=f"✏️ {prompt}",
        reply_markup=admin_cancel_kb(),
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_for_name)
async def fsm_receive_name(message: Message, state: FSMContext) -> None:
    await _save_field(message, state, "name", message.text or "")


@router.message(AdminStates.waiting_for_price)
async def fsm_receive_price(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer(
            "❌ Введите корректную цену (целое положительное число):",
            reply_markup=admin_cancel_kb(),
            parse_mode="HTML",
        )
        return
    await _save_field(message, state, "price", int(text))


@router.message(AdminStates.waiting_for_description)
async def fsm_receive_description(message: Message, state: FSMContext) -> None:
    await _save_field(message, state, "description", message.text or "")


@router.message(AdminStates.waiting_for_buy_button_text)
async def fsm_receive_buy_button(message: Message, state: FSMContext) -> None:
    await _save_field(message, state, "buy_button_text", message.text or "")


@router.message(AdminStates.waiting_for_confirm_button_text)
async def fsm_receive_confirm_button(message: Message, state: FSMContext) -> None:
    await _save_field(message, state, "confirm_button_text", message.text or "")


@router.message(AdminStates.waiting_for_price_usd)
async def fsm_receive_price_usd(message: Message, state: FSMContext) -> None:
    user = message.from_user
    raw = (message.text or "").strip().replace(",", ".")

    try:
        usd_amount = float(raw)
        if usd_amount <= 0:
            raise ValueError("non-positive")
    except ValueError:
        await message.answer(
            "❌ Введите корректную сумму в долларах, например: 3.99 или 10",
            reply_markup=admin_cancel_kb(),
            parse_mode="HTML",
        )
        return

    usd_per_rub = await get_usd_rate()
    rub_per_usd = 1.0 / usd_per_rub
    price_rub = max(1, round(usd_amount * rub_per_usd))

    logger.info(
        "Admin set USD price | user_id={} usd={} rate={:.2f} rub={}",
        user.id, usd_amount, rub_per_usd, price_rub,
    )

    await state.clear()

    factory = get_session_factory()
    async with factory() as session:
        product = await get_or_create_product(session)
        updated = await update_product_field(session, product.id, "price", price_rub)
        await session.commit()

    if not updated:
        await message.answer("❌ Ошибка при сохранении. Попробуйте снова.")
        return

    await message.answer(
        text=(
            f"✅ <b>Цена обновлена!</b>\n\n"
            f"Введено: <b>${usd_amount:.2f}</b>\n"
            f"Курс: <code>1 USD = {rub_per_usd:.2f} ₽</code>\n"
            f"Сохранено: <b>{price_rub} ₽</b>"
        ),
        parse_mode="HTML",
    )
    await message.answer(
        text=await _admin_text(updated),
        reply_markup=admin_main_kb(updated),
        parse_mode="MarkdownV2",
    )


async def _save_field(message: Message, state: FSMContext, field: str, value: str | int) -> None:
    user = message.from_user
    await state.clear()

    factory = get_session_factory()
    async with factory() as session:
        product = await get_or_create_product(session)
        updated = await update_product_field(session, product.id, field, value)
        await session.commit()

    if not updated:
        await message.answer("❌ Ошибка при сохранении. Попробуйте снова.")
        return

    logger.info("Admin updated field | user_id={} field={} value={!r}", user.id, field, value)

    await message.answer(
        text=await _admin_text(updated),
        reply_markup=admin_main_kb(updated),
        parse_mode="MarkdownV2",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# File upload
# ═══════════════════════════════════════════════════════════════════════════════

ALLOWED_FILE_TYPES: dict[str, str] = {
    "application/pdf": "PDF",
    "text/plain": "TXT",
    "application/vnd.oasis.opendocument.text": "ODT",
    "application/x-vnd.oasis.opendocument.text": "ODT",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
    "application/msword": "DOC",
}

ALLOWED_EXTENSIONS: set[str] = {".pdf", ".txt", ".odt", ".docx", ".doc"}
_FORMATS_LIST = "PDF, TXT, ODT, DOCX"


def _get_file_label(mime: str | None, filename: str | None) -> str | None:
    if mime and mime in ALLOWED_FILE_TYPES:
        return ALLOWED_FILE_TYPES[mime]
    if filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext in ALLOWED_EXTENSIONS:
            return ext.lstrip(".").upper()
    return None


@router.callback_query(F.data == "admin:upload:pdf")
async def cb_admin_upload_pdf(callback: CallbackQuery, state: FSMContext) -> None:
    user = callback.from_user
    if not _is_admin(user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_pdf)
    await callback.answer()
    logger.debug("Admin file upload initiated | user_id={}", user.id)

    await callback.message.edit_text(  # type: ignore[union-attr]
        text=(
            f"📄 <b>Загрузка файла продукта</b>\n\n"
            f"Поддерживаемые форматы: <b>{_FORMATS_LIST}</b>\n\n"
            "Отправьте файл в этот чат.\n"
            "Файл будет сохранён и автоматически отправляться покупателям."
        ),
        reply_markup=admin_cancel_kb(),
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_for_pdf, F.document)
async def fsm_receive_pdf(message: Message, state: FSMContext) -> None:
    user = message.from_user
    doc = message.document
    if not doc:
        await message.answer("❌ Файл не получен. Попробуйте снова.")
        return

    file_label = _get_file_label(doc.mime_type, doc.file_name)
    if not file_label:
        logger.warning(
            "Admin uploaded unsupported file | user_id={} mime={} name={}",
            user.id, doc.mime_type, doc.file_name,
        )
        await message.answer(
            f"⚠️ Неподдерживаемый формат файла.\n\nРазрешённые форматы: <b>{_FORMATS_LIST}</b>",
            reply_markup=admin_cancel_kb(),
            parse_mode="HTML",
        )
        return

    await state.clear()

    factory = get_session_factory()
    async with factory() as session:
        product = await get_or_create_product(session)
        updated = await update_product_field(session, product.id, "pdf_file_id", doc.file_id)
        await session.commit()

    logger.info(
        "Admin uploaded file | user_id={} product_id={} format={} file_id={}",
        user.id, product.id, file_label, doc.file_id,
    )

    if not updated:
        await message.answer("❌ Ошибка при сохранении файла.")
        return

    size_kb = doc.file_size // 1024 if doc.file_size else "?"
    await message.answer(
        text=(
            f"✅ <b>Файл успешно загружен!</b>\n\n"
            f"Формат: <b>{file_label}</b>\n"
            f"Файл: <code>{doc.file_name or 'document'}</code>\n"
            f"Размер: {size_kb} KB"
        ),
        parse_mode="HTML",
    )
    await message.answer(
        text=await _admin_text(updated),
        reply_markup=admin_main_kb(updated),
        parse_mode="MarkdownV2",
    )


@router.message(AdminStates.waiting_for_pdf)
async def fsm_pdf_wrong_type(message: Message) -> None:
    await message.answer(
        f"⚠️ Пожалуйста, отправьте файл (не фото, не текст).\n\nРазрешённые форматы: <b>{_FORMATS_LIST}</b>",
        reply_markup=admin_cancel_kb(),
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 🇬🇧 ENGLISH VERSION CUSTOMIZATION
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:customize:en_menu")
async def cb_en_customize_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Open English version customization submenu."""
    user = callback.from_user
    if not _is_admin(user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.answer()

    factory = get_session_factory()
    async with factory() as session:
        product = await get_or_create_product(session)

    def _status(val) -> str:
        return "<b>set ✅</b>" if val else "<i>fallback to RU</i>"

    text = (
        "🇬🇧 <b>English version</b>\n\n"
        "Edit the English texts shown to users with EN language.\n"
        "If a field is empty — the Russian version is shown instead.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Name: {_status(product.name_en)}\n"
        f"📝 Description: {_status(product.description_en)}\n"
        f"🏠 Welcome: {_status(product.welcome_text_en)}\n"
        f"🎉 Success: {_status(product.success_text_en)}\n"
        f"♻️ Already purchased: {_status(product.already_purchased_text_en)}\n"
        f"📎 File caption: {_status(product.file_caption_en)}\n"
        f"📜 Confirm footer: {_status(product.confirm_footer_text_en)}\n"
        f"🔘 Buy button: {_status(product.buy_button_text_en)}\n"
        f"✅ Confirm button: {_status(product.confirm_button_text_en)}\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await callback.message.edit_text(  # type: ignore[union-attr]
        text=text,
        reply_markup=admin_en_customize_kb(),
        parse_mode="HTML",
    )


# Config for EN fields
_EN_FIELD_CONFIG: dict[str, tuple[AdminStates, str, str]] = {
    "name_en": (
        AdminStates.waiting_for_name_en,
        "📦 <b>Product Name (EN)</b>",
        "Enter the product name in English.\nSend <code>reset</code> to clear (will fallback to RU).",
    ),
    "description_en": (
        AdminStates.waiting_for_description_en,
        "📝 <b>Product Description (EN)</b>",
        "Enter the product description in English.\nHTML is supported.\nSend <code>reset</code> to clear.",
    ),
    "buy_button_text_en": (
        AdminStates.waiting_for_buy_button_text_en,
        "🔘 <b>Buy Button Text (EN)</b>",
        "Enter buy button text in English.\nUse <code>{price}</code> for price substitution.\nExample: <code>💳 Buy for {price} ₽</code>\nSend <code>reset</code> to clear.",
    ),
    "confirm_button_text_en": (
        AdminStates.waiting_for_confirm_button_text_en,
        "✅ <b>Confirm Button Text (EN)</b>",
        "Enter confirm button text in English.\nExample: <code>✅ Confirm payment</code>\nSend <code>reset</code> to clear.",
    ),
    "welcome_text_en": (
        AdminStates.waiting_for_welcome_text_en,
        "🏠 <b>Welcome Text (EN)</b>",
        "Enter the /start welcome text in English.\nHTML is supported. Use <code>{name}</code> for product name.\nSend <code>reset</code> to clear.",
    ),
    "success_text_en": (
        AdminStates.waiting_for_success_text_en,
        "🎉 <b>Payment Success Text (EN)</b>",
        "Enter the text shown after successful payment in English.\nHTML is supported. Use <code>{name}</code> for product name.\nSend <code>reset</code> to clear.",
    ),
    "already_purchased_text_en": (
        AdminStates.waiting_for_already_purchased_text_en,
        "♻️ <b>Already Purchased Text (EN)</b>",
        "Enter the text for users who already bought the product.\nHTML is supported. Use <code>{name}</code> for product name.\nSend <code>reset</code> to clear.",
    ),
    "file_caption_en": (
        AdminStates.waiting_for_file_caption_en,
        "📎 <b>File Caption (EN)</b>",
        "Enter the caption shown under the sent file in English.\nUse <code>{name}</code> for product name.\nSend <code>reset</code> to clear.",
    ),
    "confirm_footer_text_en": (
        AdminStates.waiting_for_confirm_footer_text_en,
        "📜 <b>Confirm Footer Text (EN)</b>",
        "Enter the footer text shown on the confirmation screen in English.\nHTML supported (links, INN, email).\nSend <code>reset</code> to clear.",
    ),
}


@router.callback_query(F.data.startswith("admin:en:"))
async def cb_en_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    """Enter FSM state for editing an EN field."""
    user = callback.from_user
    if not _is_admin(user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    field = callback.data.split("admin:en:")[1]
    config = _EN_FIELD_CONFIG.get(field)
    if not config:
        await callback.answer("Unknown field", show_alert=True)
        return

    fsm_state, title, prompt = config
    await state.set_state(fsm_state)
    await state.update_data(field=field)
    await callback.answer()

    logger.debug("Admin EN edit field | user_id={} field={}", user.id, field)

    factory = get_session_factory()
    async with factory() as session:
        product = await get_or_create_product(session)
    current = getattr(product, field, None)
    current_block = f"\n\n<b>Current value:</b>\n<i>{current[:200] if current else 'not set (fallback to RU)'}</i>"

    await callback.message.edit_text(  # type: ignore[union-attr]
        text=f"{title}\n\n{prompt}{current_block}",
        reply_markup=admin_cancel_en_kb(),
        parse_mode="HTML",
    )


# EN field FSM receivers
@router.message(AdminStates.waiting_for_name_en)
async def fsm_receive_name_en(message: Message, state: FSMContext) -> None:
    await _save_en_field(message, state, "name_en")

@router.message(AdminStates.waiting_for_description_en)
async def fsm_receive_description_en(message: Message, state: FSMContext) -> None:
    await _save_en_field(message, state, "description_en")

@router.message(AdminStates.waiting_for_buy_button_text_en)
async def fsm_receive_buy_button_en(message: Message, state: FSMContext) -> None:
    await _save_en_field(message, state, "buy_button_text_en")

@router.message(AdminStates.waiting_for_confirm_button_text_en)
async def fsm_receive_confirm_button_en(message: Message, state: FSMContext) -> None:
    await _save_en_field(message, state, "confirm_button_text_en")

@router.message(AdminStates.waiting_for_welcome_text_en)
async def fsm_receive_welcome_text_en(message: Message, state: FSMContext) -> None:
    await _save_en_field(message, state, "welcome_text_en")

@router.message(AdminStates.waiting_for_success_text_en)
async def fsm_receive_success_text_en(message: Message, state: FSMContext) -> None:
    await _save_en_field(message, state, "success_text_en")

@router.message(AdminStates.waiting_for_already_purchased_text_en)
async def fsm_receive_already_purchased_en(message: Message, state: FSMContext) -> None:
    await _save_en_field(message, state, "already_purchased_text_en")

@router.message(AdminStates.waiting_for_file_caption_en)
async def fsm_receive_file_caption_en(message: Message, state: FSMContext) -> None:
    await _save_en_field(message, state, "file_caption_en")

@router.message(AdminStates.waiting_for_confirm_footer_text_en)
async def fsm_receive_confirm_footer_en(message: Message, state: FSMContext) -> None:
    await _save_en_field(message, state, "confirm_footer_text_en")


async def _save_en_field(message: Message, state: FSMContext, field: str) -> None:
    """Save EN text field. 'reset' clears value (fallback to RU)."""
    user = message.from_user
    raw = (message.text or "").strip()
    await state.clear()

    value = None if raw.lower() in ("reset", "сброс", "/reset") else raw

    factory = get_session_factory()
    async with factory() as session:
        product = await get_or_create_product(session)
        updated = await update_product_field(session, product.id, field, value)
        await session.commit()

    if not updated:
        await message.answer("❌ Error saving. Please try again.")
        return

    action = "reset (will fallback to RU)" if value is None else "saved"
    logger.info("Admin EN field updated | user_id={} field={} action={}", user.id, field, action)

    await message.answer(
        f"✅ <b>EN field {action}!</b>",
        parse_mode="HTML",
    )
    # Return to EN menu
    factory2 = get_session_factory()
    async with factory2() as session2:
        product2 = await get_or_create_product(session2)

    def _status(val) -> str:
        return "<b>set ✅</b>" if val else "<i>fallback to RU</i>"

    text = (
        "🇬🇧 <b>English version</b>\n\n"
        "Edit the English texts shown to users with EN language.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Name: {_status(product2.name_en)}\n"
        f"📝 Description: {_status(product2.description_en)}\n"
        f"🏠 Welcome: {_status(product2.welcome_text_en)}\n"
        f"🎉 Success: {_status(product2.success_text_en)}\n"
        f"♻️ Already purchased: {_status(product2.already_purchased_text_en)}\n"
        f"📎 File caption: {_status(product2.file_caption_en)}\n"
        f"📜 Confirm footer: {_status(product2.confirm_footer_text_en)}\n"
        f"🔘 Buy button: {_status(product2.buy_button_text_en)}\n"
        f"✅ Confirm button: {_status(product2.confirm_button_text_en)}\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await message.answer(
        text=text,
        reply_markup=admin_en_customize_kb(),
        parse_mode="HTML",
    )
