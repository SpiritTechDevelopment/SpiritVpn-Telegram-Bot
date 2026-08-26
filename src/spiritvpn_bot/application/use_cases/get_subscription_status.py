from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from spiritvpn_bot.application.ports.clock import Clock
from spiritvpn_bot.application.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class SubscriptionStatus:
    """Остаток срока подписки клиента.

    Attributes:
        days_left: сколько дней осталось (0, если срок уже истёк, но заказ
            ещё не отозван).
        expires_at: точный момент истечения — нужен, например, для заголовка
            `Subscription-Userinfo: expire=...` в ответе /s/{token}.
    """

    days_left: int
    expires_at: datetime


class GetSubscriptionStatusUseCase:
    """Остаток срока подписки клиента, для mini app Telegram."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, *, customer_id: str) -> SubscriptionStatus | None:
        """Считает остаток срока последней выдачи VPN.

        Args:
            customer_id: ID клиента.

        Returns:
            Остаток срока, либо None, если у клиента ещё не было ни одной
            выдачи.
        """
        async with self._uow as uow:
            order = await uow.orders.get_latest_for_customer(customer_id)
            await uow.commit()

        if order is None or order.expires_at is None:
            return None
        remaining = order.expires_at - self._clock.now()
        return SubscriptionStatus(days_left=max(0, remaining.days), expires_at=order.expires_at)
