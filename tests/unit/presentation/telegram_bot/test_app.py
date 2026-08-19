from __future__ import annotations

from spiritvpn_bot.presentation.telegram_bot.app import build_dispatcher
from spiritvpn_bot.presentation.telegram_bot.handlers.start import router as start_router


def test_build_dispatcher_includes_start_router() -> None:
    dp = build_dispatcher()

    assert start_router in dp.sub_routers
