"""Catalog and product view handlers — EN only."""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger

from bot.database import get_session_factory
from bot.keyboards.main_kb import product_kb, purchases_kb
from bot.services.product_service import get_or_create_product
from bot.services.purchase_service import has_purchased, get_user_purchases
from bot.services.currency import rub_to_usd, format_usd

router = Router(name="catalog")


@router.callback_query(F.data == "catalog:view")
async def cb_view_product(callback: CallbackQuery) -> None:
    """Show the product card."""
    user = callback.from_user
    await callback.answer()

    factory = get_session_factory()
    async with factory() as session:
        product = await get_or_create_product(session)
        purchased = await has_purchased(session, user.id, product.id)

    logger.info(
        "Product viewed | user_id={} product_id={} already_purchased={}",
        user.id, product.id, purchased,
    )

    usd_val = await rub_to_usd(product.price)
    price_usd = format_usd(usd_val)

    if purchased:
        text = product.get_already_purchased_text("en")
    else:
        pdf_status = "📄 File: ready to deliver\n" if product.pdf_file_id else "⚠️ File: temporarily unavailable\n"
        name = product.get_name("en")
        description = product.get_description("en")
        text = (
            f"📦 <b>{name}</b>\n\n"
            f"{description}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 Price: <b>{price_usd}</b>\n"
            f"{pdf_status}"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    await callback.message.edit_text(  # type: ignore[union-attr]
        text=text,
        reply_markup=product_kb(product, already_purchased=purchased, price_usd=price_usd),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "purchases:list")
async def cb_my_purchases(callback: CallbackQuery) -> None:
    """Show user's purchase history."""
    user = callback.from_user
    await callback.answer()

    factory = get_session_factory()
    async with factory() as session:
        purchases = await get_user_purchases(session, user.id)

    logger.debug("Purchases list | user_id={} count={}", user.id, len(purchases))

    if not purchases:
        text = (
            "📦 <b>My purchases</b>\n\n"
            "You haven't made any purchases yet.\n\n"
            "Browse the catalog to buy a product!"
        )
    else:
        lines = ["📦 <b>My purchases</b>\n"]
        for i, p in enumerate(purchases, 1):
            date_str = p.created_at.strftime("%d.%m.%Y")
            amount_str = f"{p.amount:,}".replace(",", "\u00a0")
            lines.append(f"{i}. {date_str} — <b>{amount_str} ₽</b>")
        text = "\n".join(lines)

    await callback.message.edit_text(  # type: ignore[union-attr]
        text=text,
        reply_markup=purchases_kb(),
        parse_mode="HTML",
    )
