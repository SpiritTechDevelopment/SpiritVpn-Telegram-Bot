from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from spiritvpn_bot.domain.entities.money import Money
from spiritvpn_bot.domain.entities.order import Order, OrderStatus
from spiritvpn_bot.domain.entities.plan import Plan
from spiritvpn_bot.domain.errors import InvalidOrderTransition

NOW = datetime(2026, 1, 1, tzinfo=UTC)

PLAN = Plan(
    id="nl-100gb-30d",
    title="Netherlands, 100 GB, 30 days",
    fleet_id=1,
    duration_days=30,
    quota_bytes=100 * 1024**3,
    price=Money(29900, "RUB"),
)


def make_order(status: OrderStatus = OrderStatus.CREATED) -> Order:
    order = Order(
        id="order-1",
        customer_id="tg:1",
        plan=PLAN,
        price=PLAN.price,
        status=OrderStatus.CREATED,
        created_at=NOW,
    )
    if status is not OrderStatus.CREATED:
        order.status = status
    return order


def test_new_order_starts_as_created() -> None:
    order = make_order()
    assert order.status is OrderStatus.CREATED


def test_created_moves_to_awaiting_payment() -> None:
    order = make_order()
    order.mark_awaiting_payment()
    assert order.status is OrderStatus.AWAITING_PAYMENT


def test_mark_paid_sets_command_number_and_expiry() -> None:
    order = make_order(OrderStatus.AWAITING_PAYMENT)
    expires_at = NOW + timedelta(days=30)

    order.mark_paid(command_number=1, expires_at=expires_at, payment_reference="stars:abc")

    assert order.status is OrderStatus.PAID
    assert order.command_number == 1
    assert order.expires_at == expires_at
    assert order.payment_reference == "stars:abc"


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (OrderStatus.CREATED, OrderStatus.PAID),
        (OrderStatus.CREATED, OrderStatus.ACTIVE),
        (OrderStatus.PAID, OrderStatus.AWAITING_PAYMENT),
        (OrderStatus.EXPIRED, OrderStatus.ACTIVE),
        (OrderStatus.CANCELLED, OrderStatus.AWAITING_PAYMENT),
        (OrderStatus.REFUNDED, OrderStatus.ACTIVE),
    ],
)
def test_illegal_transitions_are_rejected(start: OrderStatus, target: OrderStatus) -> None:
    order = make_order(start)
    with pytest.raises(InvalidOrderTransition):
        order.transition_to(target)


def test_terminal_statuses_accept_no_further_transitions() -> None:
    for status in (OrderStatus.EXPIRED, OrderStatus.CANCELLED, OrderStatus.REFUNDED):
        order = make_order(status)
        with pytest.raises(InvalidOrderTransition):
            order.transition_to(OrderStatus.ACTIVE)


def test_full_happy_path_lifecycle() -> None:
    order = make_order()
    order.mark_awaiting_payment()
    order.mark_paid(
        command_number=1, expires_at=NOW + timedelta(days=30), payment_reference="stars:1"
    )
    order.mark_access_requested()
    order.mark_active()
    order.transition_to(OrderStatus.EXPIRING_SOON)
    order.transition_to(OrderStatus.EXPIRED)
    assert order.status is OrderStatus.EXPIRED
