from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from spiritvpn_bot.application.errors import OrderNotFound
from spiritvpn_bot.application.use_cases.request_vpn_access import RequestAccessUseCase
from spiritvpn_bot.domain.entities.money import Money
from spiritvpn_bot.domain.entities.order import Order, OrderStatus
from spiritvpn_bot.domain.entities.plan import Plan
from tests.unit.application.fakes import (
    FakeEventPublisher,
    FakeUnitOfWork,
    FakeVPNAccessGateway,
    InMemoryCommandSequenceRepository,
    InMemoryOrderRepository,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
EXPIRES_AT = NOW + timedelta(days=30)

PLAN = Plan(
    id="nl-100gb-30d",
    title="Netherlands, 100 GB, 30 days",
    fleet_id=1,
    duration_days=30,
    quota_bytes=100 * 1024**3,
    price=Money(29900, "RUB"),
)


def paid_order(status: OrderStatus = OrderStatus.PAID) -> Order:
    order = Order(
        id="order-1",
        customer_id="tg:1",
        plan=PLAN,
        price=PLAN.price,
        status=OrderStatus.CREATED,
        created_at=NOW,
    )
    order.mark_awaiting_payment()
    order.mark_paid(command_number=1, expires_at=EXPIRES_AT, payment_reference="stars:1")
    if status is OrderStatus.ACCESS_REQUESTED:
        order.mark_access_requested()
    return order


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork(InMemoryOrderRepository(), InMemoryCommandSequenceRepository())


async def test_calls_gateway_with_order_fields(uow: FakeUnitOfWork) -> None:
    await uow.orders.add(paid_order())
    gateway = FakeVPNAccessGateway()
    use_case = RequestAccessUseCase(uow, gateway, FakeEventPublisher())

    await use_case.execute(order_id="order-1")

    assert len(gateway.applied) == 1
    call = gateway.applied[0]
    assert call.customer_id == "tg:1"
    assert call.fleet_id == PLAN.fleet_id
    assert call.quota_bytes == PLAN.quota_bytes
    assert call.expires_at == EXPIRES_AT
    assert call.command_number == 1


async def test_order_moves_to_access_requested(uow: FakeUnitOfWork) -> None:
    await uow.orders.add(paid_order())
    use_case = RequestAccessUseCase(uow, FakeVPNAccessGateway(), FakeEventPublisher())

    result = await use_case.execute(order_id="order-1")

    assert result.status is OrderStatus.ACCESS_REQUESTED


async def test_db_transaction_commits_before_gateway_is_called(uow: FakeUnitOfWork) -> None:
    await uow.orders.add(paid_order())
    gateway = FakeVPNAccessGateway(journal=uow.journal)
    use_case = RequestAccessUseCase(uow, gateway, FakeEventPublisher())

    await use_case.execute(order_id="order-1")

    commit_index = uow.journal.index("tx-commit")
    apply_index = uow.journal.index("apply_access:tg:1:1")
    assert commit_index < apply_index


async def test_retry_on_already_access_requested_order_reuses_command_number(
    uow: FakeUnitOfWork,
) -> None:
    await uow.orders.add(paid_order(OrderStatus.ACCESS_REQUESTED))
    gateway = FakeVPNAccessGateway()
    use_case = RequestAccessUseCase(uow, gateway, FakeEventPublisher())

    result = await use_case.execute(order_id="order-1")

    assert result.status is OrderStatus.ACCESS_REQUESTED
    assert gateway.applied[0].command_number == 1
    assert "save:order-1" not in uow.orders.journal


async def test_retry_after_gateway_failure_still_calls_gateway_again(
    uow: FakeUnitOfWork,
) -> None:
    order = paid_order()
    await uow.orders.add(order)
    gateway = FakeVPNAccessGateway()
    gateway.raise_on_apply = ConnectionError("spiritvpnd unreachable")
    use_case = RequestAccessUseCase(uow, gateway, FakeEventPublisher())

    with pytest.raises(ConnectionError):
        await use_case.execute(order_id="order-1")

    persisted = await uow.orders.get("order-1")
    assert persisted is not None
    assert persisted.status is OrderStatus.ACCESS_REQUESTED

    gateway.raise_on_apply = None
    result = await use_case.execute(order_id="order-1")
    assert result.status is OrderStatus.ACCESS_REQUESTED
    assert len(gateway.applied) == 1
    assert gateway.applied[0].command_number == 1


async def test_unpaid_order_is_not_sent_to_gateway(uow: FakeUnitOfWork) -> None:
    order = Order(
        id="order-1",
        customer_id="tg:1",
        plan=PLAN,
        price=PLAN.price,
        status=OrderStatus.CREATED,
        created_at=NOW,
    )
    order.mark_awaiting_payment()
    await uow.orders.add(order)
    gateway = FakeVPNAccessGateway()
    use_case = RequestAccessUseCase(uow, gateway, FakeEventPublisher())

    result = await use_case.execute(order_id="order-1")

    assert result.status is OrderStatus.AWAITING_PAYMENT
    assert gateway.applied == []


async def test_unknown_order_raises(uow: FakeUnitOfWork) -> None:
    use_case = RequestAccessUseCase(uow, FakeVPNAccessGateway(), FakeEventPublisher())

    with pytest.raises(OrderNotFound):
        await use_case.execute(order_id="missing")
