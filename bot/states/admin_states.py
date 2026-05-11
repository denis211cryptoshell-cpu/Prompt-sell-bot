"""FSM states for admin panel."""
from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """States for admin editing flow."""

    # ── Product core ───────────────────────────────────────────────────────────
    waiting_for_name = State()
    waiting_for_price = State()
    waiting_for_price_usd = State()
    waiting_for_description = State()
    waiting_for_buy_button_text = State()
    waiting_for_confirm_button_text = State()

    # ── File upload ────────────────────────────────────────────────────────────
    waiting_for_pdf = State()

    # ── Scene customization (RU) ───────────────────────────────────────────────
    waiting_for_welcome_text = State()           # /start экран
    waiting_for_success_text = State()           # экран успешной оплаты
    waiting_for_already_purchased_text = State() # экран "уже куплено"
    waiting_for_file_caption = State()           # подпись к файлу
    waiting_for_confirm_footer_text = State()    # подвал экрана подтверждения (оферта/ИНН/email)

    # ── Scene customization (EN) ───────────────────────────────────────────────
    waiting_for_name_en = State()
    waiting_for_description_en = State()
    waiting_for_buy_button_text_en = State()
    waiting_for_confirm_button_text_en = State()
    waiting_for_welcome_text_en = State()
    waiting_for_success_text_en = State()
    waiting_for_already_purchased_text_en = State()
    waiting_for_file_caption_en = State()
    waiting_for_confirm_footer_text_en = State()
