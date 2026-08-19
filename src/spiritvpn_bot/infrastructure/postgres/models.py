from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_ORDER_STATUSES = (
    "CREATED",
    "AWAITING_PAYMENT",
    "PAID",
    "ACCESS_REQUESTED",
    "ACTIVE",
    "EXPIRING_SOON",
    "EXPIRED",
    "CANCELLED",
    "REFUND_REQUESTED",
    "REFUNDED",
)


class Base(DeclarativeBase):
    pass


class OrderRow(Base):
    """Один заказ. plan_* и price_* — денормализованный снимок Plan/Money на
    момент покупки, не FK: каталог планов в БД не хранится (см.
    application/plans.py), поэтому снимок — единственный способ не потерять
    условия уже совершённой покупки при изменении каталога.
    """

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(f"status IN {_ORDER_STATUSES}", name="ck_orders_status"),
        CheckConstraint("price_amount_minor >= 0", name="ck_orders_price_non_negative"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    command_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String, nullable=True)

    plan_id: Mapped[str] = mapped_column(String, nullable=False)
    plan_title: Mapped[str] = mapped_column(String, nullable=False)
    plan_fleet_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    plan_duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_quota_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    price_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    price_currency: Mapped[str] = mapped_column(String, nullable=False)


class CommandSequenceRow(Base):
    """Последний выданный command_number на customer_id.

    spiritvpnd не выдаёт этот номер сам — эта таблица единственный источник
    истины на нашей стороне, см. domain/services/command_sequence.py.
    """

    __tablename__ = "customer_command_sequences"

    customer_id: Mapped[str] = mapped_column(String, primary_key=True)
    last_command_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
