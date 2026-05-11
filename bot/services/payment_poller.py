"""
Payment poller — background task that checks pending purchases via Robokassa API.

Used on bothost.ru and any hosting WITHOUT public ports (no webhook possible).

How it works:
  1. Every PAYMENT_POLL_INTERVAL seconds, find all purchases with status='pending'
  2. For each pending purchase, call Robokassa OpStateExt API
  3. If paid → mark as completed, send file to user
  4. If pending > PAYMENT_EXPIRE_MINUTES → mark as expired (cleanup)
"""
import asyncio
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from loguru import logger
from sqlalchemy import select

from bot.config import settings
from bot.database import get_session_factory
from bot.models.purchase import Purchase
from bot.services.robokassa import check_payment_status
from bot.services.product_service import get_or_create_product
from bot.services.user_service import get_user_lang
from bot.utils.text import no_pdf_text


async def _deliver_file(bot: Bot, user_id: int, product, lang: str = "ru") -> None:
    """Send success message and file to the user."""
    try:
        await bot.send_message(
            chat_id=user_id,
            text=product.get_success_text(lang),
            parse_mode="HTML",
        )
        if product.pdf_file_id:
            await bot.send_document(
                chat_id=user_id,
                document=product.pdf_file_id,
                caption=product.get_file_caption(lang),
            )
            logger.info("Poller: file delivered | user_id={} lang={}", user_id, lang)
        else:
            await bot.send_message(
                chat_id=user_id,
                text=no_pdf_text(lang),
                parse_mode="MarkdownV2",
            )
            logger.warning("Poller: no file to deliver | user_id={}", user_id)
    except Exception as e:
        logger.error("Poller: failed to deliver file | user_id={} error={}", user_id, e)


async def poll_pending_payments(bot: Bot) -> None:
    """
    Check all pending purchases once.
    Called repeatedly by the polling loop.
    """
    factory = get_session_factory()
    async with factory() as session:
        # Get all pending purchases
        result = await session.execute(
            select(Purchase).where(Purchase.status == "pending")
        )
        pending_list = list(result.scalars().all())

    if not pending_list:
        logger.debug("Poller: no pending purchases")
        return

    logger.debug("Poller: checking {} pending purchase(s)", len(pending_list))

    expire_after = timedelta(minutes=settings.PAYMENT_EXPIRE_MINUTES)
    now = datetime.now(tz=timezone.utc)

    for purchase in pending_list:
        # Check if purchase has expired
        created_at = purchase.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        age = now - created_at
        if age > expire_after:
            async with factory() as session:
                p = await session.get(Purchase, purchase.id)
                if p and p.status == "pending":
                    p.status = "expired"
                    await session.commit()
            logger.info(
                "Poller: purchase expired | inv_id={} user_id={} age={}m",
                purchase.id, purchase.user_id, int(age.seconds / 60),
            )
            continue

        # Check payment status via Robokassa API
        try:
            is_paid = await check_payment_status(
                inv_id=purchase.id,
                out_sum=purchase.amount,
            )
        except Exception as e:
            logger.error(
                "Poller: check_payment_status error | inv_id={} error={}",
                purchase.id, e,
            )
            continue

        if is_paid:
            # Mark as completed and deliver file
            async with factory() as session:
                p = await session.get(Purchase, purchase.id)
                if p and p.status == "pending":
                    p.status = "completed"
                    p.payment_id = f"robokassa:poll:{purchase.id}"
                    await session.commit()

                    product = await get_or_create_product(session)
                    lang = await get_user_lang(session, purchase.user_id)

            await _deliver_file(bot, purchase.user_id, product, lang=lang)
            logger.info(
                "Poller: purchase completed | inv_id={} user_id={} amount={}",
                purchase.id, purchase.user_id, purchase.amount,
            )
        else:
            logger.debug(
                "Poller: still pending | inv_id={} user_id={} age={}s",
                purchase.id, purchase.user_id, int(age.total_seconds()),
            )


async def run_payment_poller(bot: Bot) -> None:
    """
    Infinite loop that polls Robokassa for pending payment statuses.
    Runs as a background asyncio task.

    Starts only when:
      - Robokassa is configured (not demo mode)
      - PAYMENT_CHECK_MODE = 'poll'  (or webhook is not configured)
    """
    interval = settings.PAYMENT_POLL_INTERVAL
    logger.info(
        "Payment poller started | interval={}s expire={}m",
        interval, settings.PAYMENT_EXPIRE_MINUTES,
    )

    while True:
        try:
            await poll_pending_payments(bot)
        except Exception as e:
            logger.error("Payment poller iteration failed | error={}", e)

        await asyncio.sleep(interval)
