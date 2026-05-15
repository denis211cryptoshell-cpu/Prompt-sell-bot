"""Main user-facing keyboards — fully localised via i18n."""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.models.product import Product
from bot.i18n import t


def main_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Main menu keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_catalog", lang), callback_data="catalog:view")
    builder.button(text=t("btn_my_purchases", lang), callback_data="purchases:list")
    builder.button(text=t("btn_language", lang), callback_data="lang:select")
    builder.adjust(1)
    return builder.as_markup()


def product_kb(
    product: Product,
    already_purchased: bool = False,
    price_usd: str = "",
    lang: str = "ru",
) -> InlineKeyboardMarkup:
    """Product view keyboard — buy button text depends on lang."""
    builder = InlineKeyboardBuilder()
    if already_purchased:
        builder.button(
            text=t("btn_buy_already", lang),
            callback_data=f"purchase:download:{product.id}",
        )
    else:
        if lang == "en":
            buy_text = product.formatted_buy_button_en(price_usd)
        else:
            buy_text = product.formatted_buy_button(lang)
        builder.button(text=buy_text, callback_data=f"purchase:start:{product.id}")
    builder.button(text=t("btn_main_menu", lang), callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def confirm_purchase_kb(product: Product, lang: str = "ru") -> InlineKeyboardMarkup:
    """Purchase confirmation keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=product.get_confirm_button_text(lang),
        callback_data=f"purchase:confirm:{product.id}",
    )
    builder.button(text=t("btn_cancel", lang), callback_data="catalog:view")
    builder.adjust(1)
    return builder.as_markup()


def pay_with_robokassa_kb(
    pay_url: str, product_id: int, lang: str = "ru"
) -> InlineKeyboardMarkup:
    """Keyboard with URL button to open Robokassa payment page."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_pay_robokassa", lang), url=pay_url)
    builder.button(
        text=t("btn_back_to_product", lang), callback_data="catalog:view"
    )
    builder.adjust(1)
    return builder.as_markup()


def waiting_payment_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard shown while waiting for payment confirmation."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_main_menu", lang), callback_data="menu:main")
    return builder.as_markup()


def back_to_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Simple back to main menu button."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_main_menu", lang), callback_data="menu:main")
    return builder.as_markup()


def purchases_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Purchases list keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_back", lang), callback_data="menu:main")
    return builder.as_markup()
