from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from spiritvpn_bot.application.ports.updates_guard import UpdatesGuard
from spiritvpn_bot.application.use_cases.create_dev_access_link import CreateDevAccessLinkUseCase
from spiritvpn_bot.di import Container
from spiritvpn_bot.presentation.telegram_bot.handlers.start import router as start_router
from spiritvpn_bot.presentation.telegram_bot.middlewares.dedup import DedupUpdatesMiddleware

BOT_COMMANDS = [
    BotCommand(command="start", description="Начать / открыть приложение"),
    BotCommand(command="status", description="Статус подписки и серверов"),
    BotCommand(command="plans", description="Тарифы"),
    BotCommand(command="support", description="Поддержка 24/7"),
    BotCommand(command="help", description="Список команд"),
]


def build_dispatcher(*, updates_guard: UpdatesGuard) -> Dispatcher:
    dp = Dispatcher()
    dp.update.outer_middleware(DedupUpdatesMiddleware(updates_guard))
    dp.include_router(start_router)
    return dp


async def run_bot(container: Container) -> None:
    """Запускает long polling.

    Args:
        container: собранный композиционный корень (см. di.py).
    """
    bot = Bot(token=container.settings.telegram_bot_token)
    await bot.set_my_commands(BOT_COMMANDS)
    dp = build_dispatcher(updates_guard=container.updates_guard)
    dev_create_link_use_case = CreateDevAccessLinkUseCase(
        container.vpn_gateway, container.settings.friends_plan_fleet_id
    )
    await dp.start_polling(
        bot,
        redeem_friend_code_factory=container.redeem_friend_code_use_case,
        request_access_factory=container.request_access_use_case,
        get_subscription_status_factory=container.get_subscription_status_use_case,
        get_my_links_factory=container.get_my_links_use_case,
        token_signer=container.token_signer,
        subscription_base_url=container.settings.subscription_base_url,
        mini_app_url=container.settings.mini_app_url,
        support_url=container.settings.support_url,
        reviews_url=container.settings.reviews_url,
        plans=container.plans,
        dev_admin_user_ids=container.settings.dev_admin_user_id_set(),
        dev_create_link_use_case=dev_create_link_use_case,
    )
