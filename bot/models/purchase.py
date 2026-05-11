from typing import Optional

from sqlalchemy import BigInteger, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Purchase(Base):
    """Record of a completed purchase."""

    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # price at time of purchase
    payment_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # Telegram payment charge_id
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")

    user: Mapped["User"] = relationship("User", back_populates="purchases")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Purchase id={self.id} user_id={self.user_id} amount={self.amount}>"
