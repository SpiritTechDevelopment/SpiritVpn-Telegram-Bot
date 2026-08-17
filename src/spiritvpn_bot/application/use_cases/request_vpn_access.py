from __future__ import annotations

from spiritvpn_bot.application.errors import OrderNotFound
from spiritvpn_bot.application.ports.event_bus import EventPublisher
from spiritvpn_bot.application.ports.unit_of_work import UnitOfWork
from spiritvpn_bot.application.ports.vpn_gateway import VPNAccessGateway
from spiritvpn_bot.domain.entities.order import Order, OrderStatus
from spiritvpn_bot.domain.events import AccessRequested


class RequestAccessUseCase:
    """Вызывает ApplyCustomerAccess в spiritvpnd для оплаченного заказа."""

    def __init__(self, uow: UnitOfWork, gateway: VPNAccessGateway, events: EventPublisher) -> None:
        self._uow = uow
        self._gateway = gateway
        self._events = events

    async def execute(self, *, order_id: str) -> Order:
        """Запрашивает у spiritvpnd доступ по оплаченному заказу.

        Args:
            order_id: идентификатор заказа.

        Returns:
            Заказ. Если он был в статусе PAID, на выходе — ACCESS_REQUESTED;
            заказы в других статусах возвращаются без изменений.

        Raises:
            OrderNotFound: если заказа с таким order_id нет.
        """
        async with self._uow as uow:
            order = await uow.orders.get_for_update(order_id)
            if order is None:
                raise OrderNotFound(order_id)

            if order.status not in (OrderStatus.PAID, OrderStatus.ACCESS_REQUESTED):
                await uow.commit()
                return order

            if order.status is OrderStatus.PAID:
                order.mark_access_requested()
                await uow.orders.save(order)

            await uow.commit()

        assert order.command_number is not None
        assert order.expires_at is not None

        await self._gateway.apply_access(
            customer_id=order.customer_id,
            fleet_id=order.plan.fleet_id,
            quota_bytes=order.plan.quota_bytes,
            expires_at=order.expires_at,
            command_number=order.command_number,
        )

        await self._events.publish(
            AccessRequested(
                order_id=order.id,
                customer_id=order.customer_id,
                command_number=order.command_number,
            )
        )
        return order
