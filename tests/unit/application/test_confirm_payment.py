from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from spiritvpn_bot.application.errors import OrderNotFound
from spiritvpn_bot.application.use_cases.confirm_payment import ConfirmPaymentUseCase
from spiritvpn_bot.domain.entities.money import Money
from spiritvpn_bot.domain.entities.order import Order, OrderStatus
from spiritvpn_bot.domain.entities.plan import Plan
from spiritvpn_bot.domain.events import OrderPaid
from tests.unit.application.fakes import (
    FakeClock,
    FakeEventPublisher,
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


def awaiting_payment_order(order_id: str, customer_id: str) -> Order:
    order = Order(
        id=order_id,
        customer_id=customer_id,
        plan=PLAN,
        price=PLAN.price,
        status=OrderStatus.CREATED,
        created_at=NOW,
    )
    order.mark_awaiting_payment()
    return order


@pytest.fixture
def orders() -> InMemoryOrderRepository:
    return InMemoryOrderRepository()


@pytest.fixture
def command_sequence() -> InMemoryCommandSequenceRepository:
    return InMemoryCommandSequenceRepository()


@pytest.fixture
def uow(
    orders: InMemoryOrderRepository, command_sequence: InMemoryCommandSequenceRepository
) -> FakeUnitOfWork:
    return FakeUnitOfWork(orders, command_sequence)


async def test_marks_order_paid_with_expiry_and_first_command_number(
    uow: FakeUnitOfWork,
) -> None:
    order = awaiting_payment_order("order-1", "tg:1")
    await uow.orders.add(order)
    events = FakeEventPublisher()
    use_case = ConfirmPaymentUseCase(uow, FakeClock(NOW), events)

    result = await use_case.execute(order_id="order-1", payment_reference="stars:xyz")

    assert result.status is OrderStatus.PAID
    assert result.command_number == 1
    assert result.expires_at == NOW + timedelta(days=30)
    assert result.payment_reference == "stars:xyz"


async def test_second_purchase_by_same_customer_gets_next_command_number(
    uow: FakeUnitOfWork,
) -> None:
    first = awaiting_payment_order("order-1", "tg:1")
    await uow.orders.add(first)
    await ConfirmPaymentUseCase(uow, FakeClock(NOW), FakeEventPublisher()).execute(
        order_id="order-1", payment_reference="stars:1"
    )

    second = awaiting_payment_order("order-2", "tg:1")
    await uow.orders.add(second)
    result = await ConfirmPaymentUseCase(uow, FakeClock(NOW), FakeEventPublisher()).execute(
        order_id="order-2", payment_reference="stars:2"
    )

    assert result.command_number == 2


async def test_second_purchase_extends_from_existing_expiry_not_from_now(
    uow: FakeUnitOfWork,
) -> None:
    clock = FakeClock(NOW)
    first = awaiting_payment_order("order-1", "tg:1")
    await uow.orders.add(first)
    await ConfirmPaymentUseCase(uow, clock, FakeEventPublisher()).execute(
        order_id="order-1", payment_reference="stars:1"
    )

    second = awaiting_payment_order("order-2", "tg:1")
    await uow.orders.add(second)
    result = await ConfirmPaymentUseCase(uow, clock, FakeEventPublisher()).execute(
        order_id="order-2", payment_reference="stars:2"
    )

    assert result.expires_at == NOW + timedelta(days=60)


async def test_purchase_after_previous_expiry_starts_fresh_from_now(
    uow: FakeUnitOfWork,
) -> None:
    clock = FakeClock(NOW)
    first = awaiting_payment_order("order-1", "tg:1")
    await uow.orders.add(first)
    await ConfirmPaymentUseCase(uow, clock, FakeEventPublisher()).execute(
        order_id="order-1", payment_reference="stars:1"
    )

    clock.advance(timedelta(days=40))  # 10 дней после истечения первого заказа
    second = awaiting_payment_order("order-2", "tg:1")
    await uow.orders.add(second)
    result = await ConfirmPaymentUseCase(uow, clock, FakeEventPublisher()).execute(
        order_id="order-2", payment_reference="stars:2"
    )

    assert result.expires_at == NOW + timedelta(days=70)


async def test_different_customers_get_independent_command_sequences(
    uow: FakeUnitOfWork,
) -> None:
    a = awaiting_payment_order("order-a", "tg:alice")
    b = awaiting_payment_order("order-b", "tg:bob")
    await uow.orders.add(a)
    await uow.orders.add(b)

    result_a = await ConfirmPaymentUseCase(uow, FakeClock(NOW), FakeEventPublisher()).execute(
        order_id="order-a", payment_reference="stars:a"
    )
    result_b = await ConfirmPaymentUseCase(uow, FakeClock(NOW), FakeEventPublisher()).execute(
        order_id="order-b", payment_reference="stars:b"
    )

    assert result_a.command_number == 1
    assert result_b.command_number == 1


async def test_event_is_published_only_after_the_transaction_commits(
    uow: FakeUnitOfWork,
) -> None:
    order = awaiting_payment_order("order-1", "tg:1")
    await uow.orders.add(order)
    events = FakeEventPublisher(journal=uow.journal)
    use_case = ConfirmPaymentUseCase(uow, FakeClock(NOW), events)

    await use_case.execute(order_id="order-1", payment_reference="stars:xyz")

    commit_index = uow.journal.index("tx-commit")
    publish_index = uow.journal.index("publish:OrderPaid")
    assert commit_index < publish_index


async def test_publishes_order_paid_with_correct_fields(uow: FakeUnitOfWork) -> None:
    order = awaiting_payment_order("order-1", "tg:1")
    await uow.orders.add(order)
    events = FakeEventPublisher()
    use_case = ConfirmPaymentUseCase(uow, FakeClock(NOW), events)

    await use_case.execute(order_id="order-1", payment_reference="stars:xyz")

    assert events.published == [
        OrderPaid(
            order_id="order-1",
            customer_id="tg:1",
            plan_id=PLAN.id,
            command_number=1,
            expires_at=NOW + timedelta(days=30),
        )
    ]


async def test_command_sequence_locked_before_command_number_recorded(
    uow: FakeUnitOfWork,
) -> None:
    order = awaiting_payment_order("order-1", "tg:1")
    await uow.orders.add(order)
    use_case = ConfirmPaymentUseCase(uow, FakeClock(NOW), FakeEventPublisher())

    await use_case.execute(order_id="order-1", payment_reference="stars:xyz")

    lock_index = uow.command_sequence.journal.index("lock:tg:1")
    record_index = uow.command_sequence.journal.index("record:tg:1:1")
    assert lock_index < record_index


async def test_unknown_order_raises(uow: FakeUnitOfWork) -> None:
    use_case = ConfirmPaymentUseCase(uow, FakeClock(NOW), FakeEventPublisher())

    with pytest.raises(OrderNotFound):
        await use_case.execute(order_id="missing", payment_reference="stars:xyz")
