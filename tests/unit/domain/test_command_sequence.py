from __future__ import annotations

import pytest

from spiritvpn_bot.domain.errors import StaleCommandNumber
from spiritvpn_bot.domain.services.command_sequence import (
    ensure_monotonic,
    next_command_number,
)


def test_first_command_for_new_customer_is_one() -> None:
    assert next_command_number(None) == 1


def test_next_command_increments_last_issued() -> None:
    assert next_command_number(7) == 8


def test_ensure_monotonic_accepts_strictly_greater() -> None:
    ensure_monotonic(8, last_issued=7)  # must not raise


def test_ensure_monotonic_accepts_first_command() -> None:
    ensure_monotonic(1, last_issued=None)  # must not raise


@pytest.mark.parametrize("candidate", [7, 6, 1])
def test_ensure_monotonic_rejects_non_increasing(candidate: int) -> None:
    with pytest.raises(StaleCommandNumber):
        ensure_monotonic(candidate, last_issued=7)
