from __future__ import annotations

from dataclasses import dataclass

from spiritvpn_bot.domain.entities.money import Money


@dataclass(frozen=True, slots=True)
class Plan:
    """Продаваемый тариф. Соответствует ровно одному vpn_fleet_id в spiritvpnd.

    Attributes:
        id: внутренний идентификатор плана.
        title: название, которое видит пользователь.
        fleet_id: vpn_fleet_id в spiritvpnd.
        duration_days: срок действия в днях.
        quota_bytes: квота трафика в байтах на ноду.
        price: цена плана.
        purchasable: показывать ли план в публичном каталоге мини-аппа.
            У friends-free всегда False — это внутренний free план, не
            для клиентов.
        display_as_unlimited: показывать квоту клиенту как «Безлимит»,
            не выводя число. quota_bytes при этом всё равно нужен и
            остаётся реальным — это только про то, что видит клиент,
            usage_quota_bytes у spiritvpnd всегда положительное число.
    """

    id: str
    title: str
    fleet_id: int
    duration_days: int
    quota_bytes: int
    price: Money
    purchasable: bool = False
    display_as_unlimited: bool = False

    def __post_init__(self) -> None:
        if self.fleet_id <= 0:
            raise ValueError("fleet_id must be positive")
        if self.duration_days <= 0:
            raise ValueError("duration_days must be positive")
        if self.quota_bytes <= 0:
            raise ValueError("quota_bytes must be positive")
