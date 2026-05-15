"""Robokassa payment service — link generation, signature verification, status polling."""
import hashlib
from urllib.parse import urlencode
from typing import Optional
import xml.etree.ElementTree as ET

import aiohttp
from loguru import logger

from bot.config import settings


ROBOKASSA_BASE_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"


def _md5(s: str) -> str:
    """Return uppercase MD5 hex digest of a UTF-8 string."""
    return hashlib.md5(s.encode("utf-8")).hexdigest().upper()


def fmt_sum(amount_rub: int) -> str:
    """Format amount as string for Robokassa (e.g. '317.00')."""
    return f"{amount_rub}.00"


def calculate_total(base_price: int) -> dict[str, int]:
    """
    Calculate breakdown of costs including Robokassa commission.

    Robokassa deducts commission from the merchant side, meaning:
      merchant sets base_price = what they WANT to receive net.
      user pays: base_price / (1 - commission_rate)

    Returns:
        base: merchant net amount (RUB)
        commission: Robokassa commission amount (RUB)
        total: amount user actually pays (RUB)
        rate_pct: commission rate as integer percentage
    """
    rate = settings.ROBOKASSA_COMMISSION_RATE  # e.g. 0.05 = 5%
    total = round(base_price / (1 - rate))
    commission = total - base_price
    return {
        "base": base_price,
        "commission": commission,
        "total": total,
        "rate_pct": round(rate * 100),
    }


def generate_payment_link(
    inv_id: int,
    amount_rub: int,
    description: str,
    user_email: Optional[str] = None,
) -> str:
    """
    Generate Robokassa payment URL.

    Signature: MD5(MerchantLogin:OutSum:InvId:Password1)
    """
    login = settings.ROBOKASSA_LOGIN
    password1 = settings.ROBOKASSA_PASSWORD1.get_secret_value()  # type: ignore[union-attr]
    out_sum = fmt_sum(amount_rub)

    # Build signature input
    sig_parts = f"{login}:{out_sum}:{inv_id}:{password1}"
    signature = _md5(sig_parts)

    params: dict[str, str] = {
        "MerchantLogin": login,  # type: ignore[dict-item]
        "OutSum": out_sum,
        "InvId": str(inv_id),
        "Description": description[:100],  # max 100 chars
        "SignatureValue": signature,
        "Encoding": "utf-8",
        "Culture": "ru",
    }

    if user_email:
        params["Email"] = user_email

    if settings.ROBOKASSA_TEST_MODE:
        params["IsTest"] = "1"

    url = ROBOKASSA_BASE_URL + "?" + urlencode(params, quote_via=lambda s, *_: s)

    logger.debug(
        "Robokassa link generated | inv_id={} amount={} test={}",
        inv_id, out_sum, settings.ROBOKASSA_TEST_MODE,
    )
    return url


def verify_result_signature(out_sum: str, inv_id: str, signature: str) -> bool:
    """
    Verify Robokassa ResultURL notification signature.

    Robokassa sends: SignatureValue = MD5(OutSum:InvId:Password2)
    """
    if not settings.ROBOKASSA_PASSWORD2:
        logger.error("ROBOKASSA_PASSWORD2 not configured — cannot verify signature")
        return False

    password2 = settings.ROBOKASSA_PASSWORD2.get_secret_value()  # type: ignore[union-attr]
    expected = _md5(f"{out_sum}:{inv_id}:{password2}")

    is_valid = expected == signature.upper()
    if not is_valid:
        logger.warning(
            "Robokassa signature mismatch | inv_id={} expected={} got={}",
            inv_id, expected, signature.upper(),
        )
    else:
        logger.debug("Robokassa signature verified OK | inv_id={}", inv_id)

    return is_valid


# ─── Polling-based payment check (no webhook needed) ─────────────────────────

_OPSTATE_URL = "https://auth.robokassa.ru/Merchant/WebService/Service.asmx/OpStateExt"


async def check_payment_status(inv_id: int, out_sum: int) -> bool:
    """
    Check if a payment was completed by polling Robokassa OpStateExt API.

    This is an ALTERNATIVE to webhook — works on bothost.ru and any hosting
    where you cannot expose a public port.

    Signature: MD5(MerchantLogin:InvId:Password2)

    Returns True if payment was successfully completed.
    """
    if not settings.ROBOKASSA_PASSWORD2:
        logger.error("check_payment_status: ROBOKASSA_PASSWORD2 not set")
        return False

    login = settings.ROBOKASSA_LOGIN
    password2 = settings.ROBOKASSA_PASSWORD2.get_secret_value()  # type: ignore[union-attr]
    signature = _md5(f"{login}:{inv_id}:{password2}")

    params = {
        "MerchantLogin": login,
        "InvoiceID": str(inv_id),
        "Signature": signature,
    }

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        ) as session:
            async with session.get(_OPSTATE_URL, params=params) as resp:
                if resp.status != 200:
                    logger.warning(
                        "Robokassa OpStateExt HTTP error | inv_id={} status={}",
                        inv_id, resp.status,
                    )
                    return False

                text = await resp.text()
                logger.debug(
                    "Robokassa OpStateExt response | inv_id={} body={}",
                    inv_id, text[:200],
                )

                # Parse XML response
                root = ET.fromstring(text)
                # Namespace in Robokassa XML response
                ns = {"rk": "http://merchant.roboxchange.com/WebService/"}

                # Result code: 0 = OK (request processed)
                result_code_el = root.find(".//rk:Result/rk:Code", ns)
                if result_code_el is None:
                    # Try without namespace
                    result_code_el = root.find(".//Result/Code")

                if result_code_el is None or result_code_el.text != "0":
                    code = result_code_el.text if result_code_el is not None else "?"
                    logger.debug(
                        "Robokassa OpStateExt result code != 0 | inv_id={} code={}",
                        inv_id, code,
                    )
                    return False

                # State code: 100 = payment completed
                state_code_el = root.find(".//rk:State/rk:Code", ns)
                if state_code_el is None:
                    state_code_el = root.find(".//State/Code")

                if state_code_el is None:
                    logger.warning(
                        "Robokassa OpStateExt: no State/Code in response | inv_id={}",
                        inv_id,
                    )
                    return False

                state_code = state_code_el.text
                is_paid = state_code == "100"

                if is_paid:
                    logger.info(
                        "Robokassa poll: payment confirmed | inv_id={} state={}",
                        inv_id, state_code,
                    )
                else:
                    logger.debug(
                        "Robokassa poll: not paid yet | inv_id={} state={}",
                        inv_id, state_code,
                    )

                return is_paid

    except ET.ParseError as e:
        logger.error(
            "Robokassa OpStateExt XML parse error | inv_id={} error={}", inv_id, e
        )
        return False
    except Exception as e:
        logger.error(
            "Robokassa OpStateExt request failed | inv_id={} error={}", inv_id, e
        )
        return False
