"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-19

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

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


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("customer_id", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("command_number", sa.BigInteger, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_reference", sa.String, nullable=True),
        sa.Column("plan_id", sa.String, nullable=False),
        sa.Column("plan_title", sa.String, nullable=False),
        sa.Column("plan_fleet_id", sa.BigInteger, nullable=False),
        sa.Column("plan_duration_days", sa.Integer, nullable=False),
        sa.Column("plan_quota_bytes", sa.BigInteger, nullable=False),
        sa.Column("price_amount_minor", sa.BigInteger, nullable=False),
        sa.Column("price_currency", sa.String, nullable=False),
        sa.CheckConstraint(f"status IN {_ORDER_STATUSES}", name="ck_orders_status"),
        sa.CheckConstraint("price_amount_minor >= 0", name="ck_orders_price_non_negative"),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])

    op.create_table(
        "customer_command_sequences",
        sa.Column("customer_id", sa.String, primary_key=True),
        sa.Column("last_command_number", sa.BigInteger, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("customer_command_sequences")
    op.drop_table("orders")
