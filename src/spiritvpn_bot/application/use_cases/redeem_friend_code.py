from __future__ import annotations

import hmac

from spiritvpn_bot.application.builders.order_builder import OrderBuilder
from spiritvpn_bot.application.plans import FRIENDS_FREE_PLAN_ID, PlanCatalog
from spiritvpn_bot.application.ports.clock import Clock
from spiritvpn_bot.application.ports.event_bus import EventPublisher
from spiritvpn_bot.application.ports.ids import IdGenerator
from spiritvpn_bot.application.ports.unit_of_work import UnitOfWork
from spiritvpn_bot.application.use_cases._shared import assign_command_number_and_mark_paid
from spiritvpn_bot.domain.entities.order import Order
from spiritvpn_bot.domain.events import OrderPaid


class RedeemFriendCodeUseCase:
    """Бесплатный доступ по общему паролю — только для своих типов, не для клиентов."""

    def __init__(
        self,
        uow: UnitOfWork,
        id_generator: IdGenerator,
        clock: Clock,
        events: EventPublisher,
        plans: PlanCatalog,
        shared_code: str,
    ) -> None:
        self._uow = uow
        self._id_generator = id_generator
        self._clock = clock
        self._events = events
        self._plans = plans
        self._shared_code = shared_code

    async def execute(self, *, customer_id: str, submitted_code: str) -> Order | None:
        """Проверяет присланный текст на совпадение с общим паролем.

        Args:
            customer_id: непрозрачный идентификатор клиента.
            submitted_code: текст, присланный пользователем.

        Returns:
            Оплаченный заказ на friends-free план при совпадении, иначе
            None — это ожидаемый исход для произвольного текста, не ошибка.
        """
        submitted = submitted_code.strip().encode("utf-8")
        expected = self._shared_code.encode("utf-8")
        if not hmac.compare_digest(submitted, expected):
            return None

        plan = self._plans.get(FRIENDS_FREE_PLAN_ID)

        order = (
            OrderBuilder(self._id_generator, self._clock)
            .for_customer(customer_id)
            .with_plan(plan)
            .build()
        )
        order.mark_awaiting_payment()

        async with self._uow as uow:
            command_number = await assign_command_number_and_mark_paid(
                uow=uow,
                clock=self._clock,
                order=order,
                payment_reference="friend-code",
            )
            await uow.orders.add(order)
            await uow.commit()

        assert order.expires_at is not None
        await self._events.publish(
            OrderPaid(
                order_id=order.id,
                customer_id=order.customer_id,
                plan_id=order.plan.id,
                command_number=command_number,
                expires_at=order.expires_at,
            )
        )
        return order
