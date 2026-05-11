"""
Bot entry point.
Sets up loguru, initializes DB, registers routers, starts polling + Robokassa webhook server.
"""
import asyncio
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

# ── Bootstrap logger FIRST (before any other imports that might log) ──────────
from bot.logger import setup_logger
from bot.config import settings

setup_logger(log_level=settings.LOG_LEVEL, debug=settings.DEBUG)

# ── Now import everything else ────────────────────────────────────────────────
from bot.database import init_db, close_db
from bot.handlers import start, catalog, purchase, admin
from bot.handlers import language
from bot.handlers.payment_webhook import create_webhook_app
from bot.services.product_service import get_or_create_product
from bot.services.payment_poller import run_payment_poller
from bot.database import get_session_factory


async def on_startup(bot: Bot) -> None:
    """Actions on bot startup."""
    logger.info("Bot starting up...")

    # Ensure data/logs directories exist
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    # Initialize database
    await init_db()

    # Ensure default product exists
    factory = get_session_factory()
    async with factory() as session:
        product = await get_or_create_product(session)
        await session.commit()
    logger.info(
        "Product ready | id={} name={!r} price={}", product.id, product.name, product.price
    )

    # Get bot info
    bot_info = await bot.get_me()
    logger.info(
        "Bot started | @{} id={} name={!r}",
        bot_info.username, bot_info.id, bot_info.full_name,
    )
    logger.info(
        "Admin IDs: {} | Demo payment: {} | Robokassa test mode: {}",
        settings.admin_ids_list or "none configured",
        settings.is_demo_payment,
        settings.ROBOKASSA_TEST_MODE,
    )
    if not settings.is_demo_payment:
        logger.info(
            "Robokassa login={} | ResultURL={}",
            settings.ROBOKASSA_LOGIN,
            settings.robokassa_result_url,
        )


async def on_shutdown(bot: Bot) -> None:
    """Graceful shutdown."""
    logger.info("Bot shutting down...")
    await close_db()
    await bot.session.close()
    logger.info("Bot stopped. Goodbye!")


def build_dispatcher() -> Dispatcher:
    """Create and configure the dispatcher with all routers."""
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register startup/shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Include routers in priority order
    dp.include_router(admin.router)
    dp.include_router(language.router)
    dp.include_router(start.router)
    dp.include_router(catalog.router)
    dp.include_router(purchase.router)

    return dp


async def start_webhook_server(bot: Bot) -> None:
    """Start aiohttp server for Robokassa ResultURL notifications."""
    from aiohttp import web

    app = create_webhook_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.WEBHOOK_PORT)
    await site.start()
    logger.info(
        "Robokassa webhook server started | port={} path={}",
        settings.WEBHOOK_PORT,
        settings.WEBHOOK_PATH,
    )
    return runner


def _should_use_poller() -> bool:
    """Determine if payment poller should be started based on config."""
    if settings.is_demo_payment:
        return False
    mode = settings.PAYMENT_CHECK_MODE.lower()
    if mode == "poll":
        return True
    if mode == "webhook":
        return False
    # "auto": use poller if webhook host is NOT configured
    return not bool(settings.WEBHOOK_HOST.strip())


def _should_use_webhook() -> bool:
    """Determine if webhook server should be started."""
    if settings.is_demo_payment:
        return False
    mode = settings.PAYMENT_CHECK_MODE.lower()
    if mode == "webhook":
        return True
    if mode == "poll":
        return False
    # "auto": use webhook if WEBHOOK_HOST is configured
    return bool(settings.WEBHOOK_HOST.strip())


async def main() -> None:
    """
    Main async entry point.

    Starts the bot + one of two payment confirmation modes:
      - POLL mode (bothost.ru, no open ports): background task polls Robokassa API
      - WEBHOOK mode (VPS with open port): aiohttp server receives Robokassa ResultURL
    """
    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher()

    webhook_runner = None
    poller_task = None

    use_poller = _should_use_poller()
    use_webhook = _should_use_webhook()

    if use_webhook:
        try:
            webhook_runner = await start_webhook_server(bot)
            logger.info("Payment mode: WEBHOOK (ResultURL: {})", settings.robokassa_result_url)
        except Exception as e:
            logger.warning(
                "Webhook server failed to start — falling back to POLL mode | error={}", e
            )
            use_poller = True

    if use_poller:
        poller_task = asyncio.create_task(run_payment_poller(bot))
        logger.info(
            "Payment mode: POLL (interval={}s, expire={}m)",
            settings.PAYMENT_POLL_INTERVAL,
            settings.PAYMENT_EXPIRE_MINUTES,
        )

    if settings.is_demo_payment:
        logger.info("Payment mode: DEMO (no real payment, file delivered immediately)")

    logger.info("Starting bot polling...")
    _retry_delay = 3
    try:
        while True:
            try:
                await dp.start_polling(
                    bot,
                    allowed_updates=dp.resolve_used_update_types(),
                    drop_pending_updates=True,
                )
                break  # clean stop
            except (KeyboardInterrupt, SystemExit):
                logger.info("Polling stopped by user")
                break
            except Exception as e:
                err_str = str(e)
                # SSL/network glitch — retry automatically
                if any(kw in err_str for kw in ("SSL", "ClientOSError", "NetworkError", "TelegramNetworkError")):
                    logger.warning(
                        "Network error (retry in {}s): {}", _retry_delay, err_str[:120]
                    )
                    await asyncio.sleep(_retry_delay)
                    _retry_delay = min(_retry_delay * 2, 60)
                    continue
                logger.error("Fatal error in polling: {}", e)
                raise
    finally:
        if poller_task and not poller_task.done():
            poller_task.cancel()
            try:
                await poller_task
            except asyncio.CancelledError:
                pass
            logger.info("Payment poller stopped")
        if webhook_runner:
            await webhook_runner.cleanup()
            logger.info("Webhook server stopped")
        logger.info("Cleanup complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
    except Exception as e:
        logger.critical("Unhandled exception: {}", e)
        sys.exit(1)
