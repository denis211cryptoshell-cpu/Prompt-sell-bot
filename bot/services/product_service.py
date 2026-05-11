"""Product CRUD service with caching."""
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.models.product import Product
from bot.services.cache import get_cached_product, set_cached_product, invalidate_product_cache


async def get_product(session: AsyncSession) -> Optional[Product]:
    """Get the single product, using cache when possible."""
    cached = get_cached_product()
    if cached is not None:
        return cached

    logger.debug("Fetching product from DB")
    result = await session.execute(select(Product).where(Product.is_active == True).limit(1))
    product = result.scalar_one_or_none()

    if product:
        set_cached_product(product)
        logger.debug("Product loaded from DB | id={} name={!r}", product.id, product.name)
    else:
        logger.warning("No active product found in DB")

    return product


async def get_or_create_product(session: AsyncSession) -> Product:
    """Get existing product or create default one on first run."""
    product = await get_product(session)
    if product:
        return product

    logger.info("Creating default product on first run")
    product = Product(
        name=settings.DEFAULT_PRODUCT_NAME,
        description=settings.DEFAULT_PRODUCT_DESCRIPTION,
        price=settings.DEFAULT_PRODUCT_PRICE,
        buy_button_text=settings.DEFAULT_BUY_BUTTON_TEXT,
        confirm_button_text=settings.DEFAULT_CONFIRM_BUTTON_TEXT,
    )
    session.add(product)
    await session.flush()
    await session.refresh(product)
    set_cached_product(product)
    logger.info("Default product created | id={}", product.id)
    return product


async def update_product_field(
    session: AsyncSession,
    product_id: int,
    field: str,
    value: str | int,
) -> Optional[Product]:
    """Update a single field of the product."""
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        logger.warning("update_product_field: product id={} not found", product_id)
        return None

    old_value = getattr(product, field, None)
    setattr(product, field, value)
    await session.flush()
    await session.refresh(product)
    invalidate_product_cache()

    logger.info(
        "Product field updated | id={} field={} old={!r} new={!r}",
        product_id, field, old_value, value,
    )
    return product
