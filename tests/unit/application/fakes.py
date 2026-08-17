"""Тестовые двойники портов приложения."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from types import TracebackType
from typing import Self

from spiritvpn_bot.application.ports.vpn_gateway import AccessLink
from spiritvpn_bot.domain.entities.order import Order


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta


class FakeIdGenerator:
    def __init__(self, prefix: str = "order") -> None:
        self._prefix = prefix
        self._counter = 0

    def new_order_id(self) -> str:
        self._counter += 1
        return f"{self._prefix}-{self._counter}"


class InMemoryOrderRepository:
    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}
        self.journal: list[str] = []

    async def add(self, order: Order) -> None:
        self.journal.append(f"add:{order.id}")
        self._orders[order.id] = order

    async def get(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    async def get_for_update(self, order_id: str) -> Order | None:
        self.journal.append(f"lock:{order_id}")
        return self._orders.get(order_id)

    async def save(self, order: Order) -> None:
        self.journal.append(f"save:{order.id}")
        self._orders[order.id] = order


class InMemoryCommandSequenceRepository:
    def __init__(self) -> None:
        self._last: dict[str, int] = {}
        self.journal: list[str] = []

    async def last_issued_for_update(self, customer_id: str) -> int | None:
        self.journal.append(f"lock:{customer_id}")
        return self._last.get(customer_id)

    async def record(self, customer_id: str, command_number: int) -> None:
        self.journal.append(f"record:{customer_id}:{command_number}")
        self._last[customer_id] = command_number


class FakeUnitOfWork:
    """Общий журнал на orders и command_sequence сразу.

    Так тест видит, произошёл ли шаг внутри транзакции или снаружи — тот
    же приём, которым тесты spiritvpnd доказывают, что сетевой вызов
    лежит вне транзакции записи.
    """

    def __init__(
        self,
        orders: InMemoryOrderRepository,
        command_sequence: InMemoryCommandSequenceRepository,
    ) -> None:
        self.orders = orders
        self.command_sequence = command_sequence
        self.journal: list[str] = []
        self._committed = False

    async def __aenter__(self) -> Self:
        self._committed = False
        self.journal.append("tx-begin")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None or not self._committed:
            self.journal.append("tx-rollback")

    async def commit(self) -> None:
        self._committed = True
        self.journal.append("tx-commit")

    async def rollback(self) -> None:
        self.journal.append("tx-rollback")


@dataclass
class AppliedAccessCall:
    customer_id: str
    fleet_id: int
    quota_bytes: int
    expires_at: datetime
    command_number: int


class FakeVPNAccessGateway:
    def __init__(self, journal: list[str] | None = None) -> None:
        self.journal: list[str] = journal if journal is not None else []
        self.applied: list[AppliedAccessCall] = []
        self.links_by_customer: dict[str, list[AccessLink]] = {}
        self.raise_on_apply: Exception | None = None

    async def apply_access(
        self,
        *,
        customer_id: str,
        fleet_id: int,
        quota_bytes: int,
        expires_at: datetime,
        command_number: int,
    ) -> None:
        self.journal.append(f"apply_access:{customer_id}:{command_number}")
        if self.raise_on_apply is not None:
            raise self.raise_on_apply
        self.applied.append(
            AppliedAccessCall(customer_id, fleet_id, quota_bytes, expires_at, command_number)
        )

    async def get_links(self, *, customer_id: str) -> list[AccessLink]:
        self.journal.append(f"get_links:{customer_id}")
        return self.links_by_customer.get(customer_id, [])


class FakeEventPublisher:
    def __init__(self, journal: list[str] | None = None) -> None:
        self.published: list[object] = []
        self.journal: list[str] = journal if journal is not None else []

    async def publish(self, event: object) -> None:
        self.published.append(event)
        self.journal.append(f"publish:{type(event).__name__}")
