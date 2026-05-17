from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Bot ─────────────────────────────────────────────────────────────────
    BOT_TOKEN: SecretStr
    ADMIN_IDS: str = ""  # comma-separated list of admin user IDs

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/bot.db"

    # ── Robokassa ─────────────────────────────────────────────────────────────
    ROBOKASSA_LOGIN: str = ""
    # Боевые пароли (используются при ROBOKASSA_TEST_MODE=False)
    ROBOKASSA_PASSWORD1: Optional[SecretStr] = None
    ROBOKASSA_PASSWORD2: Optional[SecretStr] = None
    # Тестовые пароли (используются при ROBOKASSA_TEST_MODE=True)
    # Берутся в ЛК Robokassa → Технические настройки → Тестовый пароль #1 / #2
    ROBOKASSA_TEST_PASSWORD1: Optional[SecretStr] = None
    ROBOKASSA_TEST_PASSWORD2: Optional[SecretStr] = None
    # Commission rate as a decimal (e.g. 0.099 = 9.9%).
    # Уточните в ЛК Robokassa → Тарифы
    ROBOKASSA_COMMISSION_RATE: float = 0.05
    ROBOKASSA_TEST_MODE: bool = True   # set False to take real money

    # Webhook server settings (for Robokassa ResultURL notifications)
    WEBHOOK_HOST: str = ""           # e.g. https://yourdomain.com
    WEBHOOK_PORT: int = 8080         # internal port for aiohttp webhook server
    WEBHOOK_PATH: str = "/payment/result"

    # Payment check mode:
    #   "webhook" — Robokassa sends POST to ResultURL (VPS with open port needed)
    #   "poll"    — Bot polls Robokassa API every N seconds (bothost.ru / no open port)
    #   "auto"    — use webhook if WEBHOOK_HOST is set, else poll
    PAYMENT_CHECK_MODE: str = "auto"

    # Polling interval in seconds (used when PAYMENT_CHECK_MODE = 'poll' or 'auto')
    PAYMENT_POLL_INTERVAL: int = 30

    # How many minutes to wait before marking a pending payment as expired
    PAYMENT_EXPIRE_MINUTES: int = 60

    # ── Legacy Telegram Payments (kept for backwards compat, leave empty) ────
    PAYMENT_PROVIDER_TOKEN: Optional[str] = None

    # ── App ──────────────────────────────────────────────────────────────────
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── Product defaults (used on first run) ──────────────────────────────────
    DEFAULT_PRODUCT_NAME: str = "Пак Премиум AI-Промптов"
    DEFAULT_PRODUCT_PRICE: int = 299  # merchant net price in RUB
    DEFAULT_PRODUCT_DESCRIPTION: str = (
        "🔥 Эксклюзивная коллекция из 100+ проверенных промптов для ChatGPT, "
        "Claude и других AI-ассистентов.\n\n"
        "✅ Категории: бизнес, маркетинг, копирайтинг, программирование, творчество\n"
        "✅ Готовы к использованию прямо сейчас\n"
        "✅ Регулярные обновления включены"
    )
    DEFAULT_BUY_BUTTON_TEXT: str = "💳 Купить за {price} ₽"
    DEFAULT_CONFIRM_BUTTON_TEXT: str = "✅ Подтвердить оплату"

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def admin_ids_list(self) -> list[int]:
        if not self.ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip().isdigit()]

    @property
    def is_demo_payment(self) -> bool:
        """True when Robokassa is not configured — demo mode delivers file immediately."""
        return not (self.ROBOKASSA_LOGIN and self.ROBOKASSA_PASSWORD1 and self.ROBOKASSA_PASSWORD2)

    @property
    def robokassa_result_url(self) -> str:
        """Full URL that Robokassa will POST to on successful payment."""
        host = self.WEBHOOK_HOST.rstrip("/")
        return f"{host}{self.WEBHOOK_PATH}"


settings = Settings()
