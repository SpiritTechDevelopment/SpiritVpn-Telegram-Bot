from __future__ import annotations

from dataclasses import dataclass

from spiritvpn_bot.domain.errors import CurrencyMismatch, NegativeMoney


@dataclass(frozen=True, slots=True)
class Money:
    """Сумма в минимальных единицах валюты (копейки, центы, XTR). Не float.

    Attributes:
        amount_minor: сумма в минимальных единицах.
        currency: код валюты.
    """

    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        if self.amount_minor < 0:
            raise NegativeMoney(self.amount_minor)

    def __add__(self, other: Money) -> Money:
        self._ensure_same_currency(other)
        return Money(self.amount_minor + other.amount_minor, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._ensure_same_currency(other)
        return Money(self.amount_minor - other.amount_minor, self.currency)

    def _ensure_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise CurrencyMismatch(self.currency, other.currency)
