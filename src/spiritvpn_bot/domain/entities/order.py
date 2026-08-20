from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from spiritvpn_bot.domain.entities.money import Money
from spiritvpn_bot.domain.entities.plan import Plan
from spiritvpn_bot.domain.errors import InvalidOrderTransition


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    PAID = "PAID"
    ACCESS_REQUESTED = "ACCESS_REQUESTED"
    ACTIVE = "ACTIVE"
    EXPIRING_SOON = "EXPIRING_SOON"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    REFUND_REQUESTED = "REFUND_REQUESTED"
    REFUNDED = "REFUNDED"


# Словарь разрешённых переходов между статусами заказа.
# Ключ — текущий статус, значение — множество разрешённых целевых статусов.
_ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.CREATED: frozenset({OrderStatus.AWAITING_PAYMENT, OrderStatus.CANCELLED}),
    OrderStatus.AWAITING_PAYMENT: frozenset({OrderStatus.PAID, OrderStatus.CANCELLED}),
    OrderStatus.PAID: frozenset({OrderStatus.ACCESS_REQUESTED, OrderStatus.REFUND_REQUESTED}),
    OrderStatus.ACCESS_REQUESTED: frozenset({OrderStatus.ACTIVE, OrderStatus.REFUND_REQUESTED}),
    OrderStatus.ACTIVE: frozenset(
        {OrderStatus.EXPIRING_SOON, OrderStatus.EXPIRED, OrderStatus.REFUND_REQUESTED}
    ),
    OrderStatus.EXPIRING_SOON: frozenset(
        {OrderStatus.ACTIVE, OrderStatus.EXPIRED, OrderStatus.REFUND_REQUESTED}
    ),
    OrderStatus.EXPIRED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
    OrderStatus.REFUND_REQUESTED: frozenset({OrderStatus.REFUNDED}),
    OrderStatus.REFUNDED: frozenset(),
}


@dataclass(slots=True)
class Order:
    """Один заказ.

    Хранит снимок плана и цены на момент покупки, чтобы последующее
    изменение цены плана не переписывало историю уже созданных заказов.

    Attributes:
        id: идентификатор заказа.
        customer_id: непрозрачный идентификатор клиента для spiritvpnd.
        plan: план на момент покупки (снимок).
        price: цена на момент покупки (снимок).
        status: текущий статус заказа.
        created_at: момент создания заказа.
        command_number: номер команды ApplyCustomerAccess; назначается при оплате.
        expires_at: момент истечения доступа; назначается при оплате.
        payment_reference: ссылка на платёж у провайдера оплаты.
    """

    id: str
    customer_id: str
    plan: Plan
    price: Money
    status: OrderStatus
    created_at: datetime
    command_number: int | None = None
    expires_at: datetime | None = None
    payment_reference: str | None = None

    def transition_to(self, target: OrderStatus) -> None:
        """Переводит заказ в новый статус.

        Args:
            target: целевой статус.

        Raises:
            InvalidOrderTransition: если переход из текущего статуса в target
                не разрешён.
        """
        allowed = _ALLOWED_TRANSITIONS[self.status]
        if target not in allowed:
            raise InvalidOrderTransition(self.status.value, target.value)
        self.status = target

    def mark_awaiting_payment(self) -> None:
        self.transition_to(OrderStatus.AWAITING_PAYMENT)

    def mark_paid(
        self, *, command_number: int, expires_at: datetime, payment_reference: str
    ) -> None:
        """Фиксирует оплату и назначает command_number и expires_at.

        Args:
            command_number: номер команды для последующего ApplyCustomerAccess.
            expires_at: момент истечения доступа.
            payment_reference: ссылка на платёж у провайдера оплаты.
        """
        self.transition_to(OrderStatus.PAID)
        self.command_number = command_number
        self.expires_at = expires_at
        self.payment_reference = payment_reference

    def mark_access_requested(self) -> None:
        self.transition_to(OrderStatus.ACCESS_REQUESTED)

    def mark_active(self) -> None:
        self.transition_to(OrderStatus.ACTIVE)
