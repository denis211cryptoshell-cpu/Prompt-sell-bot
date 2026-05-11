"""Text formatting helpers for MarkdownV2."""
import re


# Characters that must be escaped in MarkdownV2
_MD2_SPECIAL = r"\_*[]()~`>#+-=|{}.!"


def escape_md(text: str) -> str:
    """Escape all MarkdownV2 special characters in a string."""
    return re.sub(r"([\_\*\[\]\(\)\~\`\>\#\+\-\=\|\{\}\.\!])", r"\\\1", text)


def fmt_price(price: int) -> str:
    """Format price with thousands separator."""
    return f"{price:,}".replace(",", " ")


WELCOME_TEXT = (
    r"🤖 *Добро пожаловать в AI Prompts Shop\!*" "\n\n"
    r"Здесь вы можете приобрести эксклюзивный пак премиум\-промптов для работы с AI\." "\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    r"🎯 *Что внутри?*" "\n"
    r"• 100\+ проверенных промптов" "\n"
    "• Категории: бизнес, маркетинг, код, творчество\n"
    "• Готовы к использованию прямо сейчас\n"
    r"• Совместимы с ChatGPT, Claude, Gemini" "\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Выберите действие ниже 👇"
)


def product_card_text(
    name: str,
    description: str,
    price: int,
    has_pdf: bool,
    price_usd: str | None = None,
) -> str:
    """Format product card for display."""
    file_status = "✅ Файл готов к отправке" if has_pdf else "⚠️ Файл ещё не загружен"
    price_fmt = fmt_price(price)

    name_esc = escape_md(name)
    desc_esc = escape_md(description)
    file_esc = escape_md(file_status)

    if price_usd:
        rub_esc = escape_md(f"~{price_fmt} ₽")
        usd_esc = escape_md(price_usd)
        price_line = f"💰 *Цена:* `{usd_esc}` \\({rub_esc}\\)"
    else:
        price_line = f"💰 *Цена:* `{price_fmt} ₽`"

    return (
        f"📦 *{name_esc}*\n\n"
        f"{desc_esc}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{price_line}\n"
        f"{file_esc}"
    )


def confirm_purchase_text(
    name: str,
    base_price: int,
    total_price: int,
    commission: int,
    rate_pct: int,
    price_usd: str,
    is_demo: bool = False,
) -> str:
    """
    Format purchase confirmation screen with full price breakdown.

    Shows:
      - Merchant price (what seller receives)
      - Robokassa commission
      - Total amount user pays
      - USD equivalent
    """
    name_esc = escape_md(name)
    base_fmt = escape_md(fmt_price(base_price) + " ₽")
    commission_fmt = escape_md(fmt_price(commission) + " ₽")
    total_fmt = escape_md(fmt_price(total_price) + " ₽")
    usd_esc = escape_md(price_usd)
    rate_esc = escape_md(f"{rate_pct}%")

    rub_hint = escape_md(f"~{fmt_price(total_price)} ₽")

    if is_demo:
        mode_line = escape_md("🧪 Режим демо — реальная оплата не требуется")
        return (
            f"🛒 *Подтверждение покупки*\n\n"
            f"📦 Товар: *{name_esc}*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Итого: *{usd_esc}* \\({rub_hint}\\)\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"_{mode_line}_\n\n"
            f"Нажмите кнопку ниже для подтверждения\\."
        )

    base_rub_hint = escape_md(f"~{fmt_price(base_price)} ₽")
    comm_rub_hint = escape_md(f"~{fmt_price(commission)} ₽")

    return (
        f"🛒 *Подтверждение покупки*\n\n"
        f"📦 Товар: *{name_esc}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 Цена продавца: `{usd_esc}` \\({base_rub_hint}\\)\n"
        f"🏦 Комиссия Robokassa \\({rate_esc}\\): `{comm_rub_hint}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 *Итого к оплате: {usd_esc}* \\({rub_hint}\\)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Нажмите кнопку ниже для перехода к оплате через Robokassa\\."
    )


def robokassa_waiting_text(
    name: str,
    total_price: int,
    price_usd: str,
    inv_id: int,
    test_mode: bool = False,
    lang: str = "ru",
) -> str:
    """Text shown after user is redirected to Robokassa payment page."""
    name_esc = escape_md(name)
    usd_esc = escape_md(price_usd)
    inv_esc = escape_md(str(inv_id))
    rub_hint = escape_md(f"~{fmt_price(total_price)} ₽")

    if lang == "en":
        test_line = escape_md("🧪 Test mode — no real money charged") if test_mode else ""
        return (
            f"💳 *Payment via Robokassa*\n\n"
            f"📦 Product: *{name_esc}*\n"
            f"💰 Amount: *{usd_esc}* \\({rub_hint}\\)\n"
            f"🔖 Order: `#{inv_esc}`\n"
            + (f"\n_{test_line}_" if test_line else "") +
            f"\n\n━━━━━━━━━━━━━━━━━━━━\n"
            f"👆 Click *«Go to payment»* button below\\.\n\n"
            f"The file will be sent automatically after payment\\."
        )

    test_line = escape_md("🧪 Тестовый режим — реальные деньги не списываются") if test_mode else ""
    return (
        f"💳 *Оплата через Robokassa*\n\n"
        f"📦 Товар: *{name_esc}*\n"
        f"💰 Сумма: *{usd_esc}* \\({rub_hint}\\)\n"
        f"🔖 Номер заказа: `#{inv_esc}`\n"
        + (f"\n_{test_line}_" if test_line else "") +
        f"\n\n━━━━━━━━━━━━━━━━━━━━\n"
        f"👆 Нажмите кнопку *«Перейти к оплате»* ниже\\.\n\n"
        f"После оплаты файл будет автоматически отправлен вам в этот чат\\."
    )


def purchase_success_text(name: str) -> str:
    """Format successful purchase message."""
    name_esc = escape_md(name)
    return (
        f"🎉 *Оплата прошла успешно\\!*\n\n"
        f"Спасибо за покупку *{name_esc}*\\!\n\n"
        f"📄 Ваш файл отправлен ниже\\. Сохраните его\\!"
    )


def already_purchased_text(name: str) -> str:
    """Format 'already purchased' message."""
    name_esc = escape_md(name)
    return (
        f"✅ *Вы уже приобрели {name_esc}\\!*\n\n"
        f"Нажмите кнопку ниже, чтобы скачать файл снова\\."
    )


def no_pdf_text(lang: str = "ru") -> str:
    if lang == "en":
        return (
            "⚠️ *File not yet uploaded*\n\n"
            "The administrator has not uploaded the file yet\\. "
            "Please try again later or contact support\\."
        )
    return (
        "⚠️ *Файл ещё не загружен*\n\n"
        "Администратор ещё не загрузил файл\\. "
        "Пожалуйста, попробуйте позже или свяжитесь с поддержкой\\."
    )


def admin_panel_text(product_name: str, price: int, has_pdf: bool, price_usd: str | None = None) -> str:
    """Admin panel header text."""
    name_esc = escape_md(product_name)
    price_fmt = escape_md(fmt_price(price))
    file_status = "✅ Загружен" if has_pdf else "❌ Не загружен"
    file_esc = escape_md(file_status)
    if price_usd:
        usd_esc = escape_md(price_usd)
        rub_esc = escape_md(f"~{fmt_price(price)} ₽")
        price_line = f"💰 Цена: *{usd_esc}* \\({rub_esc}\\)"
    else:
        price_line = f"💰 Цена \\(нетто\\): *{price_fmt} ₽*"
    return (
        f"⚙️ *Панель администратора*\n\n"
        f"📦 Продукт: *{name_esc}*\n"
        f"{price_line}\n"
        f"📄 Файл: {file_esc}\n\n"
        f"Выберите что изменить:"
    )


def admin_stats_text(total_users: int, total_purchases: int, total_revenue: int) -> str:
    """Admin statistics text."""
    revenue_fmt = escape_md(fmt_price(total_revenue))
    return (
        f"📊 *Статистика бота*\n\n"
        f"👥 Пользователей: *{total_users}*\n"
        f"🛒 Покупок: *{total_purchases}*\n"
        f"💰 Выручка: *{revenue_fmt} ₽*"
    )
