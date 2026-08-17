from __future__ import annotations

import pytest

from spiritvpn_bot.domain.entities.money import Money
from spiritvpn_bot.domain.errors import CurrencyMismatch, NegativeMoney


def test_add_same_currency() -> None:
    total = Money(1000, "RUB") + Money(500, "RUB")
    assert total == Money(1500, "RUB")


def test_subtract_same_currency() -> None:
    remainder = Money(1000, "RUB") - Money(300, "RUB")
    assert remainder == Money(700, "RUB")


def test_add_different_currency_raises() -> None:
    with pytest.raises(CurrencyMismatch):
        Money(1000, "RUB") + Money(500, "XTR")


def test_negative_amount_rejected() -> None:
    with pytest.raises(NegativeMoney):
        Money(-1, "RUB")


def test_zero_is_allowed() -> None:
    assert Money(0, "RUB").amount_minor == 0
