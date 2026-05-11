"""In-memory cache using cachetools with TTL support."""
from typing import Optional, Any

from cachetools import TTLCache
from loguru import logger

# Product cache: max 1 item, TTL 60 seconds
_product_cache: TTLCache = TTLCache(maxsize=1, ttl=60)

PRODUCT_CACHE_KEY = "current_product"


def get_cached_product() -> Optional[Any]:
    """Return cached product or None if expired/missing."""
    product = _product_cache.get(PRODUCT_CACHE_KEY)
    if product is not None:
        logger.debug("Cache HIT for product")
    else:
        logger.debug("Cache MISS for product")
    return product


def set_cached_product(product: Any) -> None:
    """Store product in cache."""
    _product_cache[PRODUCT_CACHE_KEY] = product
    logger.debug("Product cached | id={} name={!r}", product.id, product.name)


def invalidate_product_cache() -> None:
    """Remove product from cache (e.g. after admin update)."""
    _product_cache.pop(PRODUCT_CACHE_KEY, None)
    logger.debug("Product cache invalidated")
