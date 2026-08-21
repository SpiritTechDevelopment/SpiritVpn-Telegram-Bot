from __future__ import annotations

from datetime import UTC, datetime, timedelta

from spiritvpn_bot.application.use_cases.get_subscription_status import (
    GetSubscriptionStatusUseCase,
)
from spiritvpn_bot.domain.entities.money import Money
from spiritvpn_bot.domain.entities.order import Order, OrderStatus
from spiritvpn_bot.domain.entities.plan import Plan
from tests.unit.application.fakes import (
    FakeClock,
    FakeUnitOfWork,
    InMemoryCommandSequenceRepository,
    InMemoryOrderRepository,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)

PLAN = Plan(
    id="nl-30d",
    title="Netherlands, 30 days",
    fleet_id=1,
    duration_days=30,
    quota_bytes=10,
    price=Money(0, "RUB"),
)


def paid_order(order_id: str, command_number: int, expires_at: datetime) -> Order:
    order = Order(
        id=order_id,
        customer_id="tg:1",
        plan=PLAN,
        price=PLAN.price,
        status=OrderStatus.CREATED,
        created_at=NOW,
    )
    order.mark_awaiting_payment()
    order.mark_paid(command_number=command_number, expires_at=expires_at, payment_reference="x")
    return order


async def test_returns_days_left_from_the_latest_order() -> None:
    uow = FakeUnitOfWork(InMemoryOrderRepository(), InMemoryCommandSequenceRepository())
    await uow.orders.add(paid_order("order-1", 1, NOW + timedelta(days=18, hours=2)))
    use_case = GetSubscriptionStatusUseCase(uow, FakeClock(NOW))

    days_left = await use_case.execute(customer_id="tg:1")

    assert days_left == 18


async def test_uses_the_order_with_the_highest_command_number() -> None:
    uow = FakeUnitOfWork(InMemoryOrderRepository(), InMemoryCommandSequenceRepository())
    await uow.orders.add(paid_order("order-1", 1, NOW + timedelta(days=5)))
    await uow.orders.add(paid_order("order-2", 2, NOW + timedelta(days=40)))
    use_case = GetSubscriptionStatusUseCase(uow, FakeClock(NOW))

    days_left = await use_case.execute(customer_id="tg:1")

    assert days_left == 40


async def test_unknown_customer_returns_none() -> None:
    uow = FakeUnitOfWork(InMemoryOrderRepository(), InMemoryCommandSequenceRepository())
    use_case = GetSubscriptionStatusUseCase(uow, FakeClock(NOW))

    days_left = await use_case.execute(customer_id="tg:missing")

    assert days_left is None


async def test_expired_order_returns_zero_not_negative() -> None:
    uow = FakeUnitOfWork(InMemoryOrderRepository(), InMemoryCommandSequenceRepository())
    await uow.orders.add(paid_order("order-1", 1, NOW - timedelta(days=5)))
    use_case = GetSubscriptionStatusUseCase(uow, FakeClock(NOW))

    days_left = await use_case.execute(customer_id="tg:1")

    assert days_left == 0
