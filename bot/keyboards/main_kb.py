"""Main user-facing keyboards — hardcoded English."""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.models.product import Product


def main_menu_kb() -> InlineKeyboardMarkup:
    """Main menu keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍 View product", callback_data="catalog:view")
    builder.button(text="📦 My purchases", callback_data="purchases:list")
    builder.adjust(1)
    return builder.as_markup()


def product_kb(
    product: Product,
    already_purchased: bool = False,
    price_usd: str = "",
) -> InlineKeyboardMarkup:
    """Product view keyboard — price shown in USD."""
    builder = InlineKeyboardBuilder()
    if already_purchased:
        builder.button(text="📥 Download again", callback_data=f"purchase:download:{product.id}")
    else:
        buy_text = product.formatted_buy_button_en(price_usd)
        builder.button(text=buy_text, callback_data=f"purchase:start:{product.id}")
    builder.button(text="🏠 Main menu", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def confirm_purchase_kb(product: Product) -> InlineKeyboardMarkup:
    """Purchase confirmation keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=product.get_confirm_button_text("en"),
        callback_data=f"purchase:confirm:{product.id}",
    )
    builder.button(text="❌ Cancel", callback_data="catalog:view")
    builder.adjust(1)
    return builder.as_markup()


def pay_with_robokassa_kb(pay_url: str, product_id: int) -> InlineKeyboardMarkup:
    """Keyboard with URL button to open Robokassa payment page."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Go to payment", url=pay_url)
    builder.button(text="◀️ Back to product", callback_data="catalog:view")
    builder.adjust(1)
    return builder.as_markup()


def waiting_payment_kb() -> InlineKeyboardMarkup:
    """Keyboard shown while waiting for payment confirmation."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Main menu", callback_data="menu:main")
    return builder.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    """Simple back to main menu button."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Main menu", callback_data="menu:main")
    return builder.as_markup()


def purchases_kb() -> InlineKeyboardMarkup:
    """Purchases list keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Back", callback_data="menu:main")
    return builder.as_markup()
