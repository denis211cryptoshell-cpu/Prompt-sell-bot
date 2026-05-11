"""Catalog and product view handlers."""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger

from bot.database import get_session_factory
from bot.keyboards.main_kb import product_kb, purchases_kb
from bot.services.product_service import get_or_create_product
from bot.services.purchase_service import has_purchased, get_user_purchases
from bot.services.currency import rub_to_usd, format_usd
from bot.services.user_service import get_user_lang
from bot.i18n import t
from bot.utils.text import escape_md

router = Router(name="catalog")


@router.callback_query(F.data == "catalog:view")
async def cb_view_product(callback: CallbackQuery) -> None:
    """Show the product card."""
    user = callback.from_user
    await callback.answer()

    factory = get_session_factory()
    async with factory() as session:
        lang = await get_user_lang(session, user.id)
        product = await get_or_create_product(session)
        purchased = await has_purchased(session, user.id, product.id)

    logger.info(
        "Product viewed | user_id={} product_id={} already_purchased={} lang={}",
        user.id, product.id, purchased, lang,
    )

    usd_val = await rub_to_usd(product.price)
    price_usd = format_usd(usd_val)

    if purchased:
        text = product.get_already_purchased_text(lang)
    else:
        pdf_status = t("pdf_ready", lang) if product.pdf_file_id else t("pdf_missing", lang)
        text = t(
            "product_card", lang,
            name=product.get_name(lang),
            description=product.get_description(lang),
            price=product.price,
            price_usd=price_usd,
            pdf_status=pdf_status,
        )

    await callback.message.edit_text(  # type: ignore[union-attr]
        text=text,
        reply_markup=product_kb(product, already_purchased=purchased, lang=lang),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "purchases:list")
async def cb_my_purchases(callback: CallbackQuery) -> None:
    """Show user's purchase history."""
    user = callback.from_user
    await callback.answer()

    factory = get_session_factory()
    async with factory() as session:
        lang = await get_user_lang(session, user.id)
        purchases = await get_user_purchases(session, user.id)

    logger.debug("Purchases list | user_id={} count={} lang={}", user.id, len(purchases), lang)

    if not purchases:
        text = t("purchases_empty", lang)
    else:
        lines = [t("purchases_header", lang)]
        for i, p in enumerate(purchases, 1):
            date_str = p.created_at.strftime("%d.%m.%Y")
            amount_str = f"{p.amount:,}".replace(",", "\u00a0")
            lines.append(t("purchases_item", lang, n=i, date=date_str, amount=amount_str))
        text = "\n".join(lines)

    await callback.message.edit_text(  # type: ignore[union-attr]
        text=text,
        reply_markup=purchases_kb(lang),
        parse_mode="HTML",
    )
