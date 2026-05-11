"""Currency conversion service — RUB to USD using free public API with caching."""
import time
from typing import Optional

import aiohttp
from cachetools import TTLCache
from loguru import logger

# Cache exchange rate for 30 minutes
_rate_cache: TTLCache = TTLCache(maxsize=1, ttl=1800)
_CACHE_KEY = "usd_rub"

# Fallback rate if API is unavailable
_FALLBACK_RATE: float = 90.0

# Public API that doesn't require API key
_RATE_API_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/rub.json"
_RATE_API_BACKUP = "https://latest.currency-api.pages.dev/v1/currencies/rub.json"


async def get_usd_rate() -> float:
    """
    Fetch current RUB/USD exchange rate.
    Returns how many USD is 1 RUB (e.g. ~0.011).
    Caches result for 30 minutes. Falls back to last known rate on error.
    """
    # Return from cache if fresh
    if _CACHE_KEY in _rate_cache:
        rate = _rate_cache[_CACHE_KEY]
        logger.debug("Currency rate from cache | 1 RUB = {} USD", round(rate, 6))
        return rate

    # Try fetching live rate
    for url in [_RATE_API_URL, _RATE_API_BACKUP]:
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5)
            ) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        # Response: {"rub": {"usd": 0.01111, ...}}
                        usd_per_rub: float = data["rub"]["usd"]
                        _rate_cache[_CACHE_KEY] = usd_per_rub
                        logger.info(
                            "Currency rate updated | 1 RUB = {} USD (1 USD = {} RUB)",
                            round(usd_per_rub, 6),
                            round(1 / usd_per_rub, 2),
                        )
                        return usd_per_rub
        except Exception as exc:
            logger.warning("Currency API failed | url={} error={}", url, exc)
            continue

    # All APIs failed — use fallback
    fallback_rate = 1.0 / _FALLBACK_RATE
    logger.warning(
        "Using fallback currency rate | 1 USD = {} RUB", _FALLBACK_RATE
    )
    return fallback_rate


async def rub_to_usd(amount_rub: int) -> float:
    """Convert RUB amount to USD, rounded to 2 decimal places."""
    rate = await get_usd_rate()
    usd = round(amount_rub * rate, 2)
    logger.debug("Currency conversion | {} RUB = {} USD", amount_rub, usd)
    return usd


def format_usd(amount_usd: float) -> str:
    """Format USD amount for display (e.g. '$3.49')."""
    return f"${amount_usd:.2f}"


async def get_price_display(amount_rub: int) -> dict[str, str]:
    """
    Get both RUB and USD price strings for display.

    Returns:
        rub: formatted RUB string (e.g. "299 ₽")
        usd: formatted USD string (e.g. "~$3.32")
        combined: combined string (e.g. "299 ₽ (~$3.32)")
    """
    usd = await rub_to_usd(amount_rub)
    rub_str = f"{amount_rub:,}".replace(",", " ") + " ₽"
    usd_str = f"~{format_usd(usd)}"
    return {
        "rub": rub_str,
        "usd": usd_str,
        "combined": f"{rub_str} ({usd_str})",
    }
