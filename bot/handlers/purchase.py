"""Purchase flow handlers — confirmation, Robokassa payment, file delivery."""
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
    waiting_payment_kb,
)
from bot.services.product_service import get_or_create_product
from bot.services.purchase_service import (
    create_purchase,
    create_pending_purchase,
    has_purchased,
)
from bot.services.robokassa import generate_payment_link, calculate_total
from bot.services.currency import get_price_display
from bot.services.user_service import get_user_lang
from bot.utils.text import no_pdf_text, robokassa_waiting_text, fmt_price
from bot.i18n import t

router = Router(name="purchase")

_PRODUCT_ID_RE = re.compile(r"^purchase:(?:start|confirm|download):(\d+)$")


def _extract_product_id(data: str) -> Optional[int]:
    m = _PRODUCT_ID_RE.match(data)
    return int(m.group(1)) if m else None


# ─── Step 1: User clicks "Buy" ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("purchase:start:"))
async def cb_purchase_start(callback: CallbackQuery) -> None:
    """Show purchase confirmation screen with price breakdown."""
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
        logger.info("Purchase start: already purchased | user_id={}", user.id)
        await callback.message.edit_text(  # type: ignore[union-attr]
            text=product.get_already_purchased_text(lang),
            reply_markup=product_kb(product, already_purchased=True, lang=lang),
            parse_mode="HTML",
        )
        return

    # Calculate price breakdown with Robokassa commission
    breakdown = calculate_total(product.price)
    price_display = await get_price_display(breakdown["total"])

    logger.info(
        "Purchase started | user_id={} product_id={} base={} total={} commission={} lang={}",
        user.id, product.id,
        breakdown["base"], breakdown["total"], breakdown["commission"], lang,
    )

    # Build HTML confirm screen (includes DB footer: оферта/ИНН/email)
    footer = product.get_confirm_footer(lang)
    sep = t("separator", lang)
    if settings.is_demo_payment:
        confirm_text = (
            f"{t('confirm_title', lang)}\n\n"
            f"{t('confirm_product', lang, name=product.get_name(lang))}\n\n"
            f"{sep}\n"
            f"{t('confirm_price_demo', lang, price_usd=price_display['usd'], price=fmt_price(breakdown['total']))}\n"
            f"{sep}\n\n"
            f"{t('confirm_demo_note', lang)}\n\n"
            f"{sep}\n"
            f"{footer}"
        )
    else:
        confirm_text = (
            f"{t('confirm_title', lang)}\n\n"
            f"{t('confirm_product', lang, name=product.get_name(lang))}\n\n"
            f"{sep}\n"
            f"{t('confirm_price_base', lang, price_usd=price_display['usd'], price=fmt_price(breakdown['base']))}\n"
            f"{t('confirm_commission', lang, rate=breakdown['rate_pct'], commission=fmt_price(breakdown['commission']))}\n"
            f"{sep}\n"
            f"{t('confirm_total', lang, price_usd=price_display['usd'], price=fmt_price(breakdown['total']))}\n"
            f"{sep}\n\n"
            f"{footer}"
        )

    await callback.message.edit_text(  # type: ignore[union-attr]
        text=confirm_text,
        reply_markup=confirm_purchase_kb(product, lang=lang),
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
        # ── DEMO MODE: skip real payment, deliver file immediately ─────────
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
        # ── ROBOKASSA MODE: create pending purchase and send payment link ───
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
            description=product.get_name(lang)[:100],
        )

        price_display = await get_price_display(total_amount)

        logger.info(
            "Robokassa payment link generated | user_id={} inv_id={} amount={} lang={}",
            user.id, inv_id, total_amount, lang,
        )

        await callback.message.edit_text(  # type: ignore[union-attr]
            text=robokassa_waiting_text(
                name=product.get_name(lang),
                total_price=total_amount,
                price_usd=price_display["usd"],
                inv_id=inv_id,
                test_mode=settings.ROBOKASSA_TEST_MODE,
                lang=lang,
            ),
            reply_markup=pay_with_robokassa_kb(pay_url, product.id, lang=lang),
            parse_mode="MarkdownV2",
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
        err_msg = "❌ Покупка не найдена." if lang == "ru" else "❌ Purchase not found."
        await callback.answer(err_msg, show_alert=True)
        return

    if not product.pdf_file_id:
        logger.warning("Download: no file_id | user_id={} product_id={}", user.id, product.id)
        await callback.message.edit_text(  # type: ignore[union-attr]
            text=no_pdf_text(lang),
            reply_markup=back_to_menu_kb(lang),
            parse_mode="MarkdownV2",
        )
        return

    logger.info("File re-sent | user_id={} product_id={}", user.id, product.id)
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
    # Edit the current message to show success
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

    # Send file
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
        await bot.send_message(
            chat_id=chat_id,
            text=no_pdf_text(lang),
            parse_mode="MarkdownV2",
        )
