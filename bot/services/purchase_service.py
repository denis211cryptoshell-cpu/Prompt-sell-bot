"""Purchase service — create and query purchases."""
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.purchase import Purchase


async def create_purchase(
    session: AsyncSession,
    user_id: int,
    product_id: int,
    amount: int,
    payment_id: Optional[str] = None,
    status: str = "completed",
) -> Purchase:
    """Record a new purchase (default: completed for demo mode)."""
    purchase = Purchase(
        user_id=user_id,
        product_id=product_id,
        amount=amount,
        payment_id=payment_id,
        status=status,
    )
    session.add(purchase)
    await session.flush()
    await session.refresh(purchase)
    logger.info(
        "Purchase created | purchase_id={} user_id={} product_id={} amount={} status={}",
        purchase.id, user_id, product_id, amount, status,
    )
    return purchase


async def create_pending_purchase(
    session: AsyncSession,
    user_id: int,
    product_id: int,
    amount: int,
) -> Purchase:
    """
    Create a pending purchase before payment is confirmed.
    The purchase.id will be used as Robokassa InvId.
    """
    purchase = await create_purchase(
        session=session,
        user_id=user_id,
        product_id=product_id,
        amount=amount,
        status="pending",
    )
    logger.info(
        "Pending purchase created | inv_id={} user_id={} amount={}",
        purchase.id, user_id, amount,
    )
    return purchase


async def complete_purchase_by_inv_id(
    session: AsyncSession,
    inv_id: int,
    payment_id: Optional[str] = None,
) -> Optional[Purchase]:
    """
    Mark a pending purchase as completed after Robokassa confirms payment.
    Returns the updated purchase or None if not found.
    """
    result = await session.execute(
        select(Purchase).where(
            Purchase.id == inv_id,
            Purchase.status == "pending",
        )
    )
    purchase = result.scalar_one_or_none()

    if not purchase:
        logger.warning(
            "complete_purchase_by_inv_id: pending purchase not found | inv_id={}",
            inv_id,
        )
        return None

    purchase.status = "completed"
    if payment_id:
        purchase.payment_id = payment_id

    await session.flush()
    await session.refresh(purchase)

    logger.info(
        "Purchase completed via Robokassa | inv_id={} user_id={} amount={}",
        inv_id, purchase.user_id, purchase.amount,
    )
    return purchase


async def get_purchase_by_inv_id(
    session: AsyncSession,
    inv_id: int,
) -> Optional[Purchase]:
    """Get any purchase by its ID (= Robokassa InvId)."""
    result = await session.execute(
        select(Purchase).where(Purchase.id == inv_id)
    )
    return result.scalar_one_or_none()


async def has_purchased(session: AsyncSession, user_id: int, product_id: int) -> bool:
    """Check if user already has a completed purchase of this product."""
    result = await session.execute(
        select(Purchase).where(
            Purchase.user_id == user_id,
            Purchase.product_id == product_id,
            Purchase.status == "completed",
        ).limit(1)
    )
    exists = result.scalar_one_or_none() is not None
    logger.debug(
        "has_purchased check | user_id={} product_id={} result={}",
        user_id, product_id, exists,
    )
    return exists


async def get_user_purchases(session: AsyncSession, user_id: int) -> list[Purchase]:
    """Get all completed purchases for a user."""
    result = await session.execute(
        select(Purchase)
        .where(Purchase.user_id == user_id, Purchase.status == "completed")
        .order_by(Purchase.created_at.desc())
    )
    return list(result.scalars().all())
