"""Purchase flow handlers — EN only, price in USD."""
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

router = Router(name="purchase")

_PRODUCT_ID_RE = re.compile(r"^purchase:(?:start|confirm|download):(\d+)$")


def _extract_product_id(data: str) -> Optional[int]:
    m = _PRODUCT_ID_RE.match(data)
    return int(m.group(1)) if m else None


# ─── Step 1: User clicks "Buy" ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("purchase:start:"))
async def cb_purchase_start(callback: CallbackQuery) -> None:
    """Show purchase confirmation screen with price in USD."""
    user = callback.from_user
    await callback.answer()

    product_id = _extract_product_id(callback.data)
    if not product_id:
        return

    factory = get_session_factory()
    async with factory() as session:
        product = await get_or_create_product(session)
        already = await has_purchased(session, user.id, product.id)

    if already:
        logger.info("Purchase start: already purchased | user_id={}", user.id)
        usd_val = await rub_to_usd(product.price)
        price_usd = format_usd(usd_val)
        await callback.message.edit_text(  # type: ignore[union-attr]
            text=product.get_already_purchased_text("en"),
            reply_markup=product_kb(product, already_purchased=True, price_usd=price_usd),
            parse_mode="HTML",
        )
        return

    # Calculate price breakdown
    breakdown = calculate_total(product.price)
    total_amount = breakdown["total"]
    usd_val = await rub_to_usd(total_amount)
    price_usd = format_usd(usd_val)

    logger.info(
        "Purchase started | user_id={} product_id={} base={} total={} usd={}",
        user.id, product.id, breakdown["base"], total_amount, price_usd,
    )

    footer = product.get_confirm_footer("en")
    sep = "━━━━━━━━━━━━━━━━━━━━"
    name = product.get_name("en")

    if settings.is_demo_payment:
        confirm_text = (
            f"🛒 <b>Purchase confirmation</b>\n\n"
            f"📦 Product: <b>{name}</b>\n\n"
            f"{sep}\n"
            f"💰 Total: <b>{price_usd}</b>\n"
            f"{sep}\n\n"
            f"<i>🧪 Demo mode — no real payment required</i>\n\n"
            f"{sep}\n"
            f"{footer}"
        )
    else:
        usd_base = format_usd(await rub_to_usd(breakdown["base"]))
        confirm_text = (
            f"🛒 <b>Purchase confirmation</b>\n\n"
            f"📦 Product: <b>{name}</b>\n\n"
            f"{sep}\n"
            f"💵 Price: <b>{usd_base}</b>\n"
            f"🏦 Robokassa fee ({breakdown['rate_pct']}%): ~{format_usd(await rub_to_usd(breakdown['commission']))}\n"
            f"{sep}\n"
            f"💳 <b>Total: {price_usd}</b>\n"
            f"{sep}\n\n"
            f"{footer}"
        )

    await callback.message.edit_text(  # type: ignore[union-attr]
        text=confirm_text,
        reply_markup=confirm_purchase_kb(product),
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
        product = await get_or_create_product(session)

    if settings.is_demo_payment:
        logger.info(
            "Demo payment confirmed | user_id={} product_id={} amount={}",
            user.id, product.id, product.price,
        )
        await _complete_purchase(
            bot=bot,
            chat_id=user.id,
            message=callback.message,  # type: ignore[arg-type]
            user_id=user.id,
            product=product,
            payment_id="demo",
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
            description=product.get_name("en")[:100],
        )

        usd_val = await rub_to_usd(total_amount)
        price_usd = format_usd(usd_val)

        logger.info(
            "Robokassa payment link generated | user_id={} inv_id={} amount={} usd={}",
            user.id, inv_id, total_amount, price_usd,
        )

        await callback.message.edit_text(  # type: ignore[union-attr]
            text=(
                f"💳 *Payment via Robokassa*\n\n"
                f"Product: *{product.get_name('en')}*\n"
                f"Amount: *{price_usd}*\n"
                f"Order: `#{inv_id}`\n\n"
                f"Click the button below to go to the payment page\\.\n\n"
                f"_The file will be delivered automatically after payment\\._"
                + ("\n\n⚠️ _Test mode: no real money is charged_" if settings.ROBOKASSA_TEST_MODE else "")
            ),
            reply_markup=pay_with_robokassa_kb(pay_url, product.id),
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
        product = await get_or_create_product(session)
        purchased = await has_purchased(session, user.id, product.id)

    if not purchased:
        logger.warning("Download attempt without purchase | user_id={}", user.id)
        await callback.answer("❌ Purchase not found.", show_alert=True)
        return

    if not product.pdf_file_id:
        logger.warning("Download: no file_id | user_id={} product_id={}", user.id, product.id)
        await callback.message.edit_text(  # type: ignore[union-attr]
            text="⚠️ *File temporarily unavailable*\n\nThe administrator has been notified\\.",
            reply_markup=back_to_menu_kb(),
            parse_mode="MarkdownV2",
        )
        return

    logger.info("File re-sent | user_id={} product_id={}", user.id, product.id)
    await bot.send_document(
        chat_id=user.id,
        document=product.pdf_file_id,
        caption=product.get_file_caption("en"),
    )


# ─── Internal helper ──────────────────────────────────────────────────────────

async def _complete_purchase(
    bot: Bot,
    chat_id: int,
    message: Message,
    user_id: int,
    product,
    payment_id: str,
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

    success_text = product.get_success_text("en")
    try:
        await message.edit_text(
            text=success_text,
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )
    except Exception:
        await bot.send_message(
            chat_id=chat_id,
            text=success_text,
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )

    if product.pdf_file_id:
        await bot.send_document(
            chat_id=chat_id,
            document=product.pdf_file_id,
            caption=product.get_file_caption("en"),
        )
        logger.info("File delivered | user_id={} product_id={}", user_id, product.id)
    else:
        logger.warning(
            "Purchase completed but no file to deliver | user_id={} product_id={}",
            user_id, product.id,
        )
        await bot.send_message(
            chat_id=chat_id,
            text="⚠️ *File temporarily unavailable*\n\nThe administrator has been notified\\.",
            parse_mode="MarkdownV2",
        )
