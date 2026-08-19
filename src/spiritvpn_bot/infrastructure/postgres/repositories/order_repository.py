from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from spiritvpn_bot.domain.entities.money import Money
from spiritvpn_bot.domain.entities.order import Order, OrderStatus
from spiritvpn_bot.domain.entities.plan import Plan
from spiritvpn_bot.infrastructure.postgres.models import OrderRow


class PostgresOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, order: Order) -> None:
        self._session.add(_to_row(order))

    async def get(self, order_id: str) -> Order | None:
        row = await self._session.get(OrderRow, order_id)
        return _to_domain(row) if row is not None else None

    async def get_for_update(self, order_id: str) -> Order | None:
        result = await self._session.execute(
            select(OrderRow).where(OrderRow.id == order_id).with_for_update()
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row is not None else None

    async def save(self, order: Order) -> None:
        row = await self._session.get(OrderRow, order.id)
        if row is None:
            raise LookupError(f"order {order.id} not tracked by this session")
        row.status = order.status.value
        row.command_number = order.command_number
        row.expires_at = order.expires_at
        row.payment_reference = order.payment_reference


def _to_row(order: Order) -> OrderRow:
    return OrderRow(
        id=order.id,
        customer_id=order.customer_id,
        status=order.status.value,
        created_at=order.created_at,
        command_number=order.command_number,
        expires_at=order.expires_at,
        payment_reference=order.payment_reference,
        plan_id=order.plan.id,
        plan_title=order.plan.title,
        plan_fleet_id=order.plan.fleet_id,
        plan_duration_days=order.plan.duration_days,
        plan_quota_bytes=order.plan.quota_bytes,
        price_amount_minor=order.price.amount_minor,
        price_currency=order.price.currency,
    )


def _to_domain(row: OrderRow) -> Order:
    plan = Plan(
        id=row.plan_id,
        title=row.plan_title,
        fleet_id=row.plan_fleet_id,
        duration_days=row.plan_duration_days,
        quota_bytes=row.plan_quota_bytes,
        price=Money(row.price_amount_minor, row.price_currency),
    )
    return Order(
        id=row.id,
        customer_id=row.customer_id,
        plan=plan,
        price=Money(row.price_amount_minor, row.price_currency),
        status=OrderStatus(row.status),
        created_at=row.created_at,
        command_number=row.command_number,
        expires_at=row.expires_at,
        payment_reference=row.payment_reference,
    )
