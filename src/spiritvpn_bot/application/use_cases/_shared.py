from __future__ import annotations

from datetime import timedelta

from spiritvpn_bot.application.ports.clock import Clock
from spiritvpn_bot.application.ports.unit_of_work import UnitOfWork
from spiritvpn_bot.domain.entities.order import Order
from spiritvpn_bot.domain.services.command_sequence import next_command_number


async def assign_command_number_and_mark_paid(
    *, uow: UnitOfWork, clock: Clock, order: Order, payment_reference: str
) -> int:
    """Назначает command_number и переводит заказ в PAID.

    Args:
        uow: открытая транзакция UnitOfWork.
        clock: источник текущего времени.
        order: заказ в статусе AWAITING_PAYMENT.
        payment_reference: ссылка на платёж провайдера либо на бесплатную выдачу.

    Returns:
        Назначенный command_number.
    """
    last_issued = await uow.command_sequence.last_issued_for_update(order.customer_id)
    command_number = next_command_number(last_issued)
    expires_at = clock.now() + timedelta(days=order.plan.duration_days)
    order.mark_paid(
        command_number=command_number,
        expires_at=expires_at,
        payment_reference=payment_reference,
    )
    await uow.command_sequence.record(order.customer_id, command_number)
    return command_number
