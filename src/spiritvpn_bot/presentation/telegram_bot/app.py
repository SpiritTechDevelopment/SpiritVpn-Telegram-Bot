from __future__ import annotations

from aiogram import Bot, Dispatcher

from spiritvpn_bot.di import Container
from spiritvpn_bot.presentation.telegram_bot.handlers.start import router as start_router


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(start_router)
    return dp


async def run_bot(container: Container) -> None:
    """Запускает long polling.

    Args:
        container: собранный композиционный корень (см. di.py).
    """
    bot = Bot(token=container.settings.telegram_bot_token)
    dp = build_dispatcher()
    await dp.start_polling(
        bot,
        redeem_friend_code_factory=container.redeem_friend_code_use_case,
        request_access_factory=container.request_access_use_case,
        token_signer=container.token_signer,
        subscription_base_url=container.settings.subscription_base_url,
        mini_app_url=container.settings.mini_app_url,
    )
