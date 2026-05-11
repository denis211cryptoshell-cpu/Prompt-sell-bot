from typing import Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

# ── RU Defaults ───────────────────────────────────────────────────────────────
_DEFAULT_WELCOME = (
    "🤖 <b>Добро пожаловать в AI Prompts Shop!</b>\n\n"
    "Здесь вы можете приобрести эксклюзивный пак премиум-промптов для работы с AI.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🎯 <b>Что внутри?</b>\n"
    "• 100+ проверенных промптов\n"
    "• Категории: бизнес, маркетинг, код, творчество\n"
    "• Готовы к использованию прямо сейчас\n"
    "• Совместимы с ChatGPT, Claude, Gemini\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Выберите действие ниже 👇"
)

_DEFAULT_SUCCESS = (
    "🎉 <b>Оплата прошла успешно!</b>\n\n"
    "Спасибо за покупку! 📄 Ваш файл отправлен ниже. Сохраните его!"
)

_DEFAULT_ALREADY_PURCHASED = (
    "✅ <b>Вы уже приобрели этот продукт!</b>\n\n"
    "Нажмите кнопку ниже, чтобы скачать файл снова."
)

_DEFAULT_CONFIRM_FOOTER = (
    "Нажимая кнопку ниже, вы подтверждаете, что ознакомились с условиями "
    "<a href=\"https://example.com/oferta\">договора оферты</a>.\n\n"
    "ИНН: 000000000000\n"
    "Email: support@example.com"
)

# ── EN Defaults ───────────────────────────────────────────────────────────────
_DEFAULT_WELCOME_EN = (
    "🤖 <b>Welcome to AI Prompts Shop!</b>\n\n"
    "Here you can purchase an exclusive pack of premium AI prompts.\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🎯 <b>What's inside?</b>\n"
    "• 100+ tested prompts\n"
    "• Categories: business, marketing, coding, creativity\n"
    "• Ready to use right now\n"
    "• Compatible with ChatGPT, Claude, Gemini\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Choose an action below 👇"
)

_DEFAULT_SUCCESS_EN = (
    "🎉 <b>Payment successful!</b>\n\n"
    "Thank you for your purchase! 📄 Your file is sent below. Save it!"
)

_DEFAULT_ALREADY_PURCHASED_EN = (
    "✅ <b>You have already purchased this product!</b>\n\n"
    "Click the button below to download the file again."
)

_DEFAULT_CONFIRM_FOOTER_EN = (
    "By clicking the button below, you confirm that you have read the terms of the "
    "<a href=\"https://example.com/oferta\">offer agreement</a>.\n\n"
    "TIN: 000000000000\n"
    "Email: support@example.com"
)


class Product(Base):
    """Single digital product — the AI Prompts Pack."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── RU fields ─────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    pdf_file_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    buy_button_text: Mapped[str] = mapped_column(String(128), nullable=False, default="💳 Купить за {price} ₽")
    confirm_button_text: Mapped[str] = mapped_column(String(128), nullable=False, default="✅ Подтвердить оплату")
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    welcome_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    success_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    already_purchased_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_caption: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    confirm_footer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── EN fields ─────────────────────────────────────────────────────────────
    name_en: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    welcome_text_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    success_text_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    already_purchased_text_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_caption_en: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    confirm_footer_text_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    buy_button_text_en: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    confirm_button_text_en: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # ── Localised helpers ─────────────────────────────────────────────────────
    def get_name(self, lang: str = "ru") -> str:
        if lang == "en" and self.name_en:
            return self.name_en
        return self.name

    def get_description(self, lang: str = "ru") -> str:
        if lang == "en" and self.description_en:
            return self.description_en
        return self.description

    def get_welcome_text(self, lang: str = "ru") -> str:
        if lang == "en":
            # EN custom → RU custom → hardcoded EN default
            return self.welcome_text_en or self.welcome_text or _DEFAULT_WELCOME_EN
        return self.welcome_text or _DEFAULT_WELCOME

    def get_success_text(self, lang: str = "ru") -> str:
        if lang == "en":
            t = self.success_text_en or self.success_text or _DEFAULT_SUCCESS_EN
        else:
            t = self.success_text or _DEFAULT_SUCCESS
        return t.replace("{name}", self.get_name(lang))

    def get_already_purchased_text(self, lang: str = "ru") -> str:
        if lang == "en":
            t = self.already_purchased_text_en or self.already_purchased_text or _DEFAULT_ALREADY_PURCHASED_EN
        else:
            t = self.already_purchased_text or _DEFAULT_ALREADY_PURCHASED
        return t.replace("{name}", self.get_name(lang))

    def get_file_caption(self, lang: str = "ru") -> str:
        if lang == "en":
            t = self.file_caption_en or self.file_caption or "📄 {name}"
        else:
            t = self.file_caption or "📄 {name}"
        return t.replace("{name}", self.get_name(lang))

    def get_confirm_footer(self, lang: str = "ru") -> str:
        if lang == "en":
            # EN custom → RU custom → hardcoded EN default
            return self.confirm_footer_text_en or self.confirm_footer_text or _DEFAULT_CONFIRM_FOOTER_EN
        return self.confirm_footer_text or _DEFAULT_CONFIRM_FOOTER

    def get_buy_button_text(self, lang: str = "ru") -> str:
        if lang == "en" and self.buy_button_text_en:
            return self.buy_button_text_en
        return self.buy_button_text

    def get_confirm_button_text(self, lang: str = "ru") -> str:
        if lang == "en" and self.confirm_button_text_en:
            return self.confirm_button_text_en
        return self.confirm_button_text

    def formatted_buy_button(self, lang: str = "ru") -> str:
        return self.get_buy_button_text(lang).replace("{price}", str(self.price))

    def formatted_buy_button_en(self, price_usd: str = "") -> str:
        """Buy button with USD price. Uses EN custom text if set, else default."""
        template = self.buy_button_text_en or "💳 Buy for {price}"
        return template.replace("{price}", price_usd or "—")

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name!r} price={self.price}>"
