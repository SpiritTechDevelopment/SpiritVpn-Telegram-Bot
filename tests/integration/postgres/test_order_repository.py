from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spiritvpn_bot.domain.entities.money import Money
from spiritvpn_bot.domain.entities.order import Order, OrderStatus
from spiritvpn_bot.domain.entities.plan import Plan
from spiritvpn_bot.infrastructure.postgres.repositories.order_repository import (
    PostgresOrderRepository,
)
from spiritvpn_bot.infrastructure.postgres.unit_of_work import SqlAlchemyUnitOfWork

NOW = datetime(2026, 1, 1, tzinfo=UTC)

PLAN = Plan(
    id="nl-100gb-30d",
    title="Netherlands, 100 GB, 30 days",
    fleet_id=1,
    duration_days=30,
    quota_bytes=100 * 1024**3,
    price=Money(29900, "RUB"),
)


def make_order(order_id: str = "order-1", status: OrderStatus = OrderStatus.CREATED) -> Order:
    order = Order(
        id=order_id,
        customer_id="tg:1",
        plan=PLAN,
        price=PLAN.price,
        status=OrderStatus.CREATED,
        created_at=NOW,
    )
    if status is not OrderStatus.CREATED:
        order.status = status
    return order


async def test_add_then_get_roundtrips_all_fields(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    order = make_order()
    async with session_factory() as session:
        await PostgresOrderRepository(session).add(order)
        await session.commit()

    async with session_factory() as session:
        loaded = await PostgresOrderRepository(session).get("order-1")

    assert loaded is not None
    assert loaded.id == order.id
    assert loaded.customer_id == order.customer_id
    assert loaded.status is OrderStatus.CREATED
    assert loaded.created_at == NOW
    assert loaded.plan == PLAN
    assert loaded.price == PLAN.price
    assert loaded.command_number is None
    assert loaded.expires_at is None
    assert loaded.payment_reference is None


async def test_get_missing_order_returns_none(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        loaded = await PostgresOrderRepository(session).get("missing")
    assert loaded is None


async def test_save_persists_paid_fields(uow: SqlAlchemyUnitOfWork) -> None:
    order = make_order()
    async with uow as tx:
        await tx.orders.add(order)
        await tx.commit()

    expires_at = NOW + timedelta(days=30)
    async with uow as tx:
        loaded = await tx.orders.get_for_update("order-1")
        assert loaded is not None
        loaded.mark_awaiting_payment()
        loaded.mark_paid(command_number=1, expires_at=expires_at, payment_reference="stars:1")
        await tx.orders.save(loaded)
        await tx.commit()

    async with uow as tx:
        reloaded = await tx.orders.get_for_update("order-1")
        await tx.commit()

    assert reloaded is not None
    assert reloaded.status is OrderStatus.PAID
    assert reloaded.command_number == 1
    assert reloaded.expires_at == expires_at
    assert reloaded.payment_reference == "stars:1"


async def test_uow_rolls_back_without_explicit_commit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    uow = SqlAlchemyUnitOfWork(session_factory)
    order = make_order()

    async with uow as tx:
        await tx.orders.add(order)
        # намеренно без commit()

    async with session_factory() as session:
        loaded = await PostgresOrderRepository(session).get("order-1")

    assert loaded is None


async def test_get_for_update_serializes_concurrent_writers(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    order = make_order()
    async with SqlAlchemyUnitOfWork(session_factory) as tx:
        await tx.orders.add(order)
        await tx.commit()

    holder = SqlAlchemyUnitOfWork(session_factory)
    async with holder as holding_tx:
        await holding_tx.orders.get_for_update("order-1")

        second = SqlAlchemyUnitOfWork(session_factory)

        async def second_reader() -> None:
            async with second as tx:
                await tx.orders.get_for_update("order-1")
                await tx.commit()

        task = asyncio.ensure_future(second_reader())
        await asyncio.sleep(0.2)
        assert not task.done(), "второй читатель не должен был получить блокировку"

        await holding_tx.commit()
        await asyncio.wait_for(task, timeout=2)
        assert task.done()
