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
    """

    id: str
    title: str
    fleet_id: int
    duration_days: int
    quota_bytes: int
    price: Money

    def __post_init__(self) -> None:
        if self.fleet_id <= 0:
            raise ValueError("fleet_id must be positive")
        if self.duration_days <= 0:
            raise ValueError("duration_days must be positive")
        if self.quota_bytes <= 0:
            raise ValueError("quota_bytes must be positive")
