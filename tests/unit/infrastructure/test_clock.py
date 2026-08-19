from __future__ import annotations

from datetime import UTC

from spiritvpn_bot.infrastructure.clock import SystemClock


def test_now_returns_aware_utc_datetime() -> None:
    result = SystemClock().now()

    assert result.tzinfo is UTC
