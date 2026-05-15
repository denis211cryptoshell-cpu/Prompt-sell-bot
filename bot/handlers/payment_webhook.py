"""
Robokassa webhook handler (aiohttp server).

Robokassa sends three notifications:
  ResultURL — server-to-server POST (we verify signature and complete the purchase)
  SuccessURL — user browser redirect after payment (not used for logic)
  FailURL   — user browser redirect on failure (not used for logic)

Only ResultURL matters for business logic.
Flow:
  1. Robokassa POSTs to ResultURL with OutSum, InvId, SignatureValue
  2. We verify the signature using Password2
  3. We complete the purchase in DB
  4. We deliver the file to the Telegram user
  5. We respond with "OK{InvId}" which Robokassa requires
"""
from aiohttp import web
from loguru import logger

from bot.config import settings
from bot.database import get_session_factory
from bot.services.robokassa import verify_result_signature
from bot.services.purchase_service import (
    complete_purchase_by_inv_id,
    get_purchase_by_inv_id,
)
from bot.services.product_service import get_or_create_product
from bot.services.user_service import get_user_lang


async def handle_result_url(request: web.Request) -> web.Response:
    """
    Handle Robokassa ResultURL POST notification.
    Must respond with 'OK{InvId}' on success, else Robokassa retries.
    """
    try:
        # Accept both POST form-data and GET query params (Robokassa can do both)
        if request.method == "POST":
            data = await request.post()
        else:
            data = request.rel_url.query

        out_sum = data.get("OutSum", "")
        inv_id = data.get("InvId", "")
        signature = data.get("SignatureValue", "")

        logger.info(
            "Robokassa ResultURL received | inv_id={} out_sum={} sig={}",
            inv_id, out_sum, signature[:8] + "...",
        )

        if not all([out_sum, inv_id, signature]):
            logger.warning("Robokassa ResultURL: missing params | data={}", dict(data))
            return web.Response(text="MISSING_PARAMS", status=400)

        # Verify signature
        if not verify_result_signature(out_sum, inv_id, signature):
            logger.error(
                "Robokassa signature verification FAILED | inv_id={}", inv_id
            )
            return web.Response(text="BAD_SIGNATURE", status=403)

        inv_id_int = int(inv_id)

        # Complete purchase in DB
        factory = get_session_factory()
        async with factory() as session:
            purchase = await complete_purchase_by_inv_id(
                session=session,
                inv_id=inv_id_int,
                payment_id=f"robokassa:{inv_id}:{out_sum}",
            )
            if not purchase:
                # May already be completed (duplicate notification — OK to ignore)
                existing = await get_purchase_by_inv_id(session, inv_id_int)
                if existing and existing.status == "completed":
                    logger.info(
                        "Robokassa duplicate notification | inv_id={} — already completed",
                        inv_id,
                    )
                    return web.Response(text=f"OK{inv_id}")
                logger.error(
                    "Robokassa ResultURL: purchase not found | inv_id={}", inv_id
                )
                return web.Response(text="NOT_FOUND", status=404)

            user_id = purchase.user_id
            product = await get_or_create_product(session)
            lang = await get_user_lang(session, user_id)
            await session.commit()

        # Deliver file to user via Telegram bot
        bot = request.app["bot"]
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
                logger.info(
                    "File delivered after Robokassa payment | user_id={} inv_id={} lang={}",
                    user_id, inv_id, lang,
                )
            else:
                no_file_text = (
                    "⚠️ <b>Файл временно недоступен</b>\n\nАдминистратор уже уведомлён."
                    if lang == "ru"
                    else "⚠️ <b>File temporarily unavailable</b>\n\nThe administrator has been notified."
                )
                await bot.send_message(
                    chat_id=user_id,
                    text=no_file_text,
                    parse_mode="HTML",
                )
                logger.warning(
                    "Payment received but no file to deliver | user_id={} inv_id={} lang={}",
                    user_id, inv_id, lang,
                )
        except Exception as e:
            # Don't fail the webhook — purchase is already recorded
            logger.error(
                "Failed to send file after payment | user_id={} inv_id={} error={}",
                user_id, inv_id, e,
            )

        # REQUIRED: respond with OK{InvId} so Robokassa marks payment as complete
        logger.info("Robokassa payment fully processed | inv_id={}", inv_id)
        return web.Response(text=f"OK{inv_id}")

    except Exception as e:
        logger.error("Robokassa ResultURL handler exception | error={}", e, exc_info=True)
        return web.Response(text="ERROR", status=500)


async def handle_success_url(request: web.Request) -> web.Response:
    """User browser redirect after successful payment — show friendly HTML."""
    inv_id = request.rel_url.query.get("InvId", "")
    logger.debug("Robokassa SuccessURL visit | inv_id={}", inv_id)
    html = """
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <title>Оплата прошла успешно</title>
    <style>body{font-family:sans-serif;text-align:center;padding:60px;background:#f0f9f0;}
    h1{color:#27ae60;}p{color:#555;}</style></head>
    <body>
    <h1>✅ Оплата прошла успешно!</h1>
    <p>Вернитесь в Telegram — файл уже отправлен вам в бот.</p>
    </body></html>
    """
    return web.Response(text=html, content_type="text/html")


async def handle_fail_url(request: web.Request) -> web.Response:
    """User browser redirect on failed payment."""
    inv_id = request.rel_url.query.get("InvId", "")
    logger.info("Robokassa FailURL visit | inv_id={}", inv_id)
    html = """
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <title>Ошибка оплаты</title>
    <style>body{font-family:sans-serif;text-align:center;padding:60px;background:#fff5f5;}
    h1{color:#e74c3c;}p{color:#555;}</style></head>
    <body>
    <h1>❌ Оплата не прошла</h1>
    <p>Вернитесь в Telegram и попробуйте снова.</p>
    </body></html>
    """
    return web.Response(text=html, content_type="text/html")


def create_webhook_app(bot) -> web.Application:
    """Create aiohttp app for Robokassa webhooks."""
    app = web.Application()
    app["bot"] = bot

    path = settings.WEBHOOK_PATH
    app.router.add_route("POST", path, handle_result_url)
    app.router.add_route("GET", path, handle_result_url)  # some Robokassa configs use GET
    app.router.add_route("GET", "/payment/success", handle_success_url)
    app.router.add_route("GET", "/payment/fail", handle_fail_url)

    logger.info(
        "Webhook app created | result_url={} port={}",
        path, settings.WEBHOOK_PORT,
    )
    return app
