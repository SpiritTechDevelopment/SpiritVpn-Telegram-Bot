from __future__ import annotations

from datetime import UTC, datetime

import pytest

from spiritvpn_bot.application.use_cases.purchase_subscription import (
    PurchaseSubscriptionUseCase,
)
from spiritvpn_bot.domain.entities.money import Money
from spiritvpn_bot.domain.entities.order import OrderStatus
from spiritvpn_bot.domain.entities.plan import Plan
from tests.unit.application.fakes import (
    FakeClock,
    FakeIdGenerator,
    FakeUnitOfWork,
    InMemoryCommandSequenceRepository,
    InMemoryOrderRepository,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)

PLAN = Plan(
    id="nl-100gb-30d",
    title="Netherlands, 100 GB, 30 days",
    fleet_id=1,
    duration_days=30,
    quota_bytes=100 * 1024**3,
    price=Money(29900, "RUB"),
)


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork(InMemoryOrderRepository(), InMemoryCommandSequenceRepository())


async def test_creates_order_in_awaiting_payment(uow: FakeUnitOfWork) -> None:
    use_case = PurchaseSubscriptionUseCase(uow, FakeIdGenerator(), FakeClock(NOW))

    order = await use_case.execute(customer_id="tg:42", plan=PLAN)

    assert order.status is OrderStatus.AWAITING_PAYMENT
    assert order.customer_id == "tg:42"
    assert order.plan is PLAN
    assert order.price == PLAN.price
    assert order.created_at == NOW


async def test_order_is_persisted_and_committed(uow: FakeUnitOfWork) -> None:
    use_case = PurchaseSubscriptionUseCase(uow, FakeIdGenerator(), FakeClock(NOW))

    order = await use_case.execute(customer_id="tg:42", plan=PLAN)

    assert await uow.orders.get(order.id) is order
    assert uow.journal == ["tx-begin", "tx-commit"]


async def test_each_purchase_gets_a_fresh_order_id(uow: FakeUnitOfWork) -> None:
    use_case = PurchaseSubscriptionUseCase(uow, FakeIdGenerator(), FakeClock(NOW))

    first = await use_case.execute(customer_id="tg:1", plan=PLAN)
    second = await use_case.execute(customer_id="tg:2", plan=PLAN)

    assert first.id != second.id
