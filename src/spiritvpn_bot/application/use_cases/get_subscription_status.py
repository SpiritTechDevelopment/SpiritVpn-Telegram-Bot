from __future__ import annotations

from spiritvpn_bot.application.ports.clock import Clock
from spiritvpn_bot.application.ports.unit_of_work import UnitOfWork


class GetSubscriptionStatusUseCase:
    """Остаток срока подписки клиента, для mini app Telegram."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, *, customer_id: str) -> int | None:
        """Считает, сколько дней осталось до истечения последней выдачи VPN.

        Args:
            customer_id: ID клиента.

        Returns:
            Число дней (0, если срок уже истёк, но заказ ещё не отозван),
            либо None, если у клиента ещё не было ни одной выдачи.
        """
        async with self._uow as uow:
            order = await uow.orders.get_latest_for_customer(customer_id)
            await uow.commit()

        if order is None or order.expires_at is None:
            return None
        remaining = order.expires_at - self._clock.now()
        return max(0, remaining.days)
