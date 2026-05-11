"""Admin panel keyboards."""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.models.product import Product


def admin_main_kb(product: Product) -> InlineKeyboardMarkup:
    """Admin main menu — compact, organized."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Название продукта", callback_data="admin:edit:name")
    builder.button(text="💰 Цена ($)", callback_data="admin:edit:price_usd")
    builder.button(text="📝 Описание", callback_data="admin:edit:description")
    builder.button(text="📄 Загрузить файл", callback_data="admin:upload:pdf")
    builder.button(text="🎨 Кастомизация", callback_data="admin:customize:menu")
    builder.button(text="👁 Предпросмотр", callback_data="admin:preview")
    builder.button(text="📊 Статистика", callback_data="admin:stats")
    builder.button(text="❌ Закрыть", callback_data="admin:close")
    builder.adjust(1)
    return builder.as_markup()


def admin_customize_kb() -> InlineKeyboardMarkup:
    """Customization submenu — one button per bot scene."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🏠 Приветствие (/start)",
        callback_data="admin:customize:welcome_text",
    )
    builder.button(
        text="📦 Карточка товара (название)",
        callback_data="admin:edit:name",
    )
    builder.button(
        text="📝 Описание товара",
        callback_data="admin:edit:description",
    )
    builder.button(
        text="🔘 Кнопка «Купить»",
        callback_data="admin:edit:buy_button_text",
    )
    builder.button(
        text="✅ Кнопка «Подтвердить»",
        callback_data="admin:edit:confirm_button_text",
    )
    builder.button(
        text="🎉 Текст «Оплата прошла»",
        callback_data="admin:customize:success_text",
    )
    builder.button(
        text="♻️ Текст «Уже куплено»",
        callback_data="admin:customize:already_purchased_text",
    )
    builder.button(
        text="📎 Подпись к файлу",
        callback_data="admin:customize:file_caption",
    )
    builder.button(
        text="📜 Подвал подтверждения (оферта/ИНН)",
        callback_data="admin:customize:confirm_footer_text",
    )
    builder.button(
        text="◀️ Назад",
        callback_data="admin:menu",
    )
    builder.adjust(1)
    return builder.as_markup()


def admin_back_kb() -> InlineKeyboardMarkup:
    """Back to admin menu button."""
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад в админ-панель", callback_data="admin:menu")
    return builder.as_markup()


def admin_back_customize_kb() -> InlineKeyboardMarkup:
    """Back to customization submenu."""
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад в кастомизацию", callback_data="admin:customize:menu")
    builder.button(text="🏠 Главное меню", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def admin_cancel_kb() -> InlineKeyboardMarkup:
    """Cancel current admin action."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="admin:menu")
    return builder.as_markup()


def admin_cancel_customize_kb() -> InlineKeyboardMarkup:
    """Cancel and go back to customization menu."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="admin:customize:menu")
    return builder.as_markup()


def admin_pdf_confirm_kb() -> InlineKeyboardMarkup:
    """Confirm or cancel PDF upload."""
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад в админ-панель", callback_data="admin:menu")
    return builder.as_markup()
