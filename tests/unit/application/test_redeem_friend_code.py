from __future__ import annotations

from datetime import UTC, datetime, timedelta

from spiritvpn_bot.application.plans import build_plan_catalog
from spiritvpn_bot.application.use_cases.redeem_friend_code import RedeemFriendCodeUseCase
from spiritvpn_bot.domain.events import OrderPaid
from tests.unit.application.fakes import (
    FakeClock,
    FakeEventPublisher,
    FakeIdGenerator,
    FakeUnitOfWork,
    InMemoryCommandSequenceRepository,
    InMemoryOrderRepository,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
PLANS = build_plan_catalog(friends_fleet_id=1, friends_quota_bytes=10, friends_duration_days=30)
SHARED_CODE = "letmein"


def build_use_case(
    uow: FakeUnitOfWork, events: FakeEventPublisher | None = None
) -> RedeemFriendCodeUseCase:
    return RedeemFriendCodeUseCase(
        uow,
        FakeIdGenerator(),
        FakeClock(NOW),
        events or FakeEventPublisher(),
        PLANS,
        SHARED_CODE,
    )


def make_uow() -> FakeUnitOfWork:
    return FakeUnitOfWork(InMemoryOrderRepository(), InMemoryCommandSequenceRepository())


async def test_correct_code_creates_a_paid_order() -> None:
    uow = make_uow()
    use_case = build_use_case(uow)

    order = await use_case.execute(customer_id="tg:1", submitted_code=SHARED_CODE)

    assert order is not None
    assert order.customer_id == "tg:1"
    assert order.plan.id == "friends-free"
    assert order.price.amount_minor == 0
    assert order.command_number == 1
    assert order.payment_reference == "friend-code"
    assert order.expires_at == NOW + timedelta(days=30)


async def test_wrong_code_returns_none_without_touching_the_database() -> None:
    uow = make_uow()
    use_case = build_use_case(uow)

    order = await use_case.execute(customer_id="tg:1", submitted_code="wrong")

    assert order is None
    assert uow.orders.journal == []


async def test_code_is_trimmed_of_surrounding_whitespace() -> None:
    uow = make_uow()
    use_case = build_use_case(uow)

    order = await use_case.execute(customer_id="tg:1", submitted_code=f"  {SHARED_CODE}  ")

    assert order is not None


async def test_same_code_grants_access_to_multiple_customers() -> None:
    uow = make_uow()
    use_case = build_use_case(uow)

    first = await use_case.execute(customer_id="tg:1", submitted_code=SHARED_CODE)
    second = await use_case.execute(customer_id="tg:2", submitted_code=SHARED_CODE)

    assert first is not None
    assert second is not None
    assert first.id != second.id
    assert first.command_number == 1
    assert second.command_number == 1  # независимые счётчики на клиента


async def test_repeated_use_by_the_same_customer_renews() -> None:
    uow = make_uow()
    use_case = build_use_case(uow)

    first = await use_case.execute(customer_id="tg:1", submitted_code=SHARED_CODE)
    second = await use_case.execute(customer_id="tg:1", submitted_code=SHARED_CODE)

    assert first is not None
    assert second is not None
    assert second.command_number == 2


async def test_test_duration_code_grants_a_short_lived_order() -> None:
    uow = make_uow()
    use_case = build_use_case(uow)

    order = await use_case.execute(customer_id="tg:1", submitted_code="test10m")

    assert order is not None
    assert order.plan.id == "friends-free"
    assert order.expires_at == NOW + timedelta(minutes=10)


async def test_different_test_duration_codes_grant_different_durations() -> None:
    uow = make_uow()
    use_case = build_use_case(uow)

    order = await use_case.execute(customer_id="tg:1", submitted_code="test1h")

    assert order is not None
    assert order.expires_at == NOW + timedelta(hours=1)


async def test_publishes_order_paid_only_on_match() -> None:
    uow = make_uow()
    events = FakeEventPublisher()
    use_case = build_use_case(uow, events)

    await use_case.execute(customer_id="tg:1", submitted_code="wrong")
    assert events.published == []

    await use_case.execute(customer_id="tg:1", submitted_code=SHARED_CODE)
    assert len(events.published) == 1
    assert isinstance(events.published[0], OrderPaid)
