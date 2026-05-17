"""Purchase flow handlers — fully localised, price in user's currency."""
import re
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from loguru import logger

from bot.config import settings
from bot.database import get_session_factory
from bot.keyboards.main_kb import (
    confirm_purchase_kb,
    back_to_menu_kb,
    product_kb,
    pay_with_robokassa_kb,
)
from bot.services.product_service import get_or_create_product
from bot.services.purchase_service import (
    create_purchase,
    create_pending_purchase,
    has_purchased,
)
from bot.services.robokassa import generate_payment_link, calculate_total
from bot.services.currency import rub_to_usd, format_usd
from bot.services.user_service import get_user_lang
from bot.i18n import t

router = Router(name="purchase")

_PRODUCT_ID_RE = re.compile(r"^purchase:(?:start|confirm|download):(\d+)$")


def _extract_product_id(data: str) -> Optional[int]:
    m = _PRODUCT_ID_RE.match(data)
    return int(m.group(1)) if m else None


# ─── Step 1: User clicks "Buy" ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("purchase:start:"))
async def cb_purchase_start(callback: CallbackQuery) -> None:
    """Show purchase confirmation screen."""
    user = callback.from_user
    await callback.answer()

    product_id = _extract_product_id(callback.data)
    if not product_id:
        return

    factory = get_session_factory()
    async with factory() as session:
        lang = await get_user_lang(session, user.id)
        product = await get_or_create_product(session)
        already = await has_purchased(session, user.id, product.id)

    if already:
        logger.info("Purchase start: already purchased | user_id={} lang={}", user.id, lang)
        usd_val = await rub_to_usd(product.price)
        price_usd = format_usd(usd_val)
        await callback.message.edit_text(  # type: ignore[union-attr]
            text=product.get_already_purchased_text(lang),
            reply_markup=product_kb(product, already_purchased=True, price_usd=price_usd, lang=lang),
            parse_mode="HTML",
        )
        return

    # Calculate price breakdown
    breakdown = calculate_total(product.price)
    total_amount = breakdown["total"]
    usd_val = await rub_to_usd(total_amount)
    price_usd = format_usd(usd_val)

    logger.info(
        "Purchase started | user_id={} product_id={} base={} total={} usd={} lang={}",
        user.id, product.id, breakdown["base"], total_amount, price_usd, lang,
    )

    footer = product.get_confirm_footer(lang)
    sep = t("separator", lang)
    name = product.get_name(lang)

    if settings.is_demo_payment:
        if lang == "ru":
            price_line = f"💰 Итого: <b>{total_amount:,} ₽</b> (~{price_usd})".replace(",", "\u00a0")
        else:
            price_line = f"💰 Total: <b>{price_usd}</b>"
        confirm_text = (
            f"{t('confirm_title', lang)}\n\n"
            f"{t('confirm_product', lang, name=name)}\n\n"
            f"{sep}\n"
            f"{price_line}\n"
            f"{sep}\n\n"
            f"{t('confirm_demo_note', lang)}\n\n"
            f"{sep}\n"
            f"{footer}"
        )
    else:
        usd_base = format_usd(await rub_to_usd(breakdown["base"]))
        usd_commission = format_usd(await rub_to_usd(breakdown["commission"]))
        if lang == "ru":
            base_line = f"💵 Цена продавца: <b>{breakdown['base']:,} ₽</b> (~{usd_base})".replace(",", "\u00a0")
            commission_line = f"🏦 Комиссия Robokassa ({breakdown['rate_pct']}%): ~{breakdown['commission']:,} ₽".replace(",", "\u00a0")
            total_line = f"💳 <b>Итого к оплате: {total_amount:,} ₽</b> (~{price_usd})".replace(",", "\u00a0")
        else:
            base_line = f"💵 Seller price: <b>{usd_base}</b>"
            commission_line = f"🏦 Robokassa fee ({breakdown['rate_pct']}%): ~{usd_commission}"
            total_line = f"💳 <b>Total: {price_usd}</b>"
        confirm_text = (
            f"{t('confirm_title', lang)}\n\n"
            f"{t('confirm_product', lang, name=name)}\n\n"
            f"{sep}\n"
            f"{base_line}\n"
            f"{commission_line}\n"
            f"{sep}\n"
            f"{total_line}\n"
            f"{sep}\n\n"
            f"{footer}"
        )

    await callback.message.edit_text(  # type: ignore[union-attr]
        text=confirm_text,
        reply_markup=confirm_purchase_kb(product, lang),
        parse_mode="HTML",
    )


# ─── Step 2: User confirms purchase ───────────────────────────────────────────

@router.callback_query(F.data.startswith("purchase:confirm:"))
async def cb_purchase_confirm(callback: CallbackQuery, bot: Bot) -> None:
    """Process payment — demo mode or Robokassa redirect."""
    user = callback.from_user
    await callback.answer()

    product_id = _extract_product_id(callback.data)
    if not product_id:
        return

    factory = get_session_factory()
    async with factory() as session:
        lang = await get_user_lang(session, user.id)
        product = await get_or_create_product(session)

    if settings.is_demo_payment:
        logger.info(
            "Demo payment confirmed | user_id={} product_id={} amount={} lang={}",
            user.id, product.id, product.price, lang,
        )
        await _complete_purchase(
            bot=bot,
            chat_id=user.id,
            message=callback.message,  # type: ignore[arg-type]
            user_id=user.id,
            product=product,
            payment_id="demo",
            lang=lang,
        )
    else:
        breakdown = calculate_total(product.price)
        total_amount = breakdown["total"]

        async with factory() as session:
            pending = await create_pending_purchase(
                session=session,
                user_id=user.id,
                product_id=product.id,
                amount=total_amount,
            )
            await session.commit()
            inv_id = pending.id

        pay_url = generate_payment_link(
            inv_id=inv_id,
            amount_rub=total_amount,
            description=product.get_name(lang),
            lang=lang,
        )

        usd_val = await rub_to_usd(total_amount)
        price_usd = format_usd(usd_val)

        logger.info(
            "Robokassa payment link generated | user_id={} inv_id={} amount={} usd={} lang={}",
            user.id, inv_id, total_amount, price_usd, lang,
        )

        if lang == "ru":
            amount_str = f"{total_amount:,} ₽".replace(",", "\u00a0") + f" (~{price_usd})"
        else:
            amount_str = price_usd

        test_note = ""
        if settings.ROBOKASSA_TEST_MODE:
            test_note = "\n\n" + (
                "⚠️ <i>Тестовый режим: реальные деньги не списываются</i>"
                if lang == "ru"
                else "⚠️ <i>Test mode: no real money is charged</i>"
            )

        # For EN users: explain that payment page shows RUB (Russian rubles)
        rub_note = ""
        if lang == "en":
            rub_note = (
                f"\n\n⚠️ <i>The payment page displays the price in Russian Rubles (₽).\n"
                f"Amount: <b>{total_amount:,} ₽</b> ≈ <b>{price_usd}</b>\n"
                f"Your bank will convert automatically at the current rate.</i>"
            ).replace(",", "\u00a0")

        await callback.message.edit_text(  # type: ignore[union-attr]
            text=(
                f"💳 <b>{'Оплата через Robokassa' if lang == 'ru' else 'Payment via Robokassa'}</b>\n\n"
                f"📦 {'Товар' if lang == 'ru' else 'Product'}: <b>{product.get_name(lang)}</b>\n"
                f"💵 {'Сумма' if lang == 'ru' else 'Amount'}: <b>{amount_str}</b>\n"
                f"🔖 {'Заказ' if lang == 'ru' else 'Order'}: <code>#{inv_id}</code>\n\n"
                f"{'Нажмите кнопку ниже для перехода на страницу оплаты.' if lang == 'ru' else 'Click the button below to go to the payment page.'}\n\n"
                f"<i>{'Файл будет доставлен автоматически после оплаты.' if lang == 'ru' else 'The file will be delivered automatically after payment.'}</i>"
                f"{rub_note}"
                f"{test_note}"
            ),
            reply_markup=pay_with_robokassa_kb(pay_url, product.id, lang),
            parse_mode="HTML",
        )


# ─── Download again ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("purchase:download:"))
async def cb_download_again(callback: CallbackQuery, bot: Bot) -> None:
    """Re-send file to user who already purchased."""
    user = callback.from_user
    await callback.answer()

    factory = get_session_factory()
    async with factory() as session:
        lang = await get_user_lang(session, user.id)
        product = await get_or_create_product(session)
        purchased = await has_purchased(session, user.id, product.id)

    if not purchased:
        logger.warning("Download attempt without purchase | user_id={}", user.id)
        no_purchase_text = (
            "❌ Покупка не найдена." if lang == "ru" else "❌ Purchase not found."
        )
        await callback.answer(no_purchase_text, show_alert=True)
        return

    if not product.pdf_file_id:
        logger.warning("Download: no file_id | user_id={} product_id={}", user.id, product.id)
        no_file_text = (
            "⚠️ <b>Файл временно недоступен</b>\n\nАдминистратор уже уведомлён."
            if lang == "ru"
            else "⚠️ <b>File temporarily unavailable</b>\n\nThe administrator has been notified."
        )
        await callback.message.edit_text(  # type: ignore[union-attr]
            text=no_file_text,
            reply_markup=back_to_menu_kb(lang),
            parse_mode="HTML",
        )
        return

    logger.info("File re-sent | user_id={} product_id={} lang={}", user.id, product.id, lang)
    await bot.send_document(
        chat_id=user.id,
        document=product.pdf_file_id,
        caption=product.get_file_caption(lang),
    )


# ─── Internal helper ──────────────────────────────────────────────────────────

async def _complete_purchase(
    bot: Bot,
    chat_id: int,
    message: Message,
    user_id: int,
    product,
    payment_id: str,
    lang: str = "ru",
) -> None:
    """Record completed purchase in DB and deliver file to user."""
    factory = get_session_factory()
    async with factory() as session:
        await create_purchase(
            session=session,
            user_id=user_id,
            product_id=product.id,
            amount=product.price,
            payment_id=payment_id,
            status="completed",
        )
        await session.commit()

    success_text = product.get_success_text(lang)
    try:
        await message.edit_text(
            text=success_text,
            reply_markup=back_to_menu_kb(lang),
            parse_mode="HTML",
        )
    except Exception:
        await bot.send_message(
            chat_id=chat_id,
            text=success_text,
            reply_markup=back_to_menu_kb(lang),
            parse_mode="HTML",
        )

    if product.pdf_file_id:
        await bot.send_document(
            chat_id=chat_id,
            document=product.pdf_file_id,
            caption=product.get_file_caption(lang),
        )
        logger.info("File delivered | user_id={} product_id={} lang={}", user_id, product.id, lang)
    else:
        logger.warning(
            "Purchase completed but no file to deliver | user_id={} product_id={}",
            user_id, product.id,
        )
        no_file_text = (
            "⚠️ <b>Файл временно недоступен</b>\n\nАдминистратор уже уведомлён."
            if lang == "ru"
            else "⚠️ <b>File temporarily unavailable</b>\n\nThe administrator has been notified."
        )
        await bot.send_message(
            chat_id=chat_id,
            text=no_file_text,
            parse_mode="HTML",
        )
