"""Точка входа процесса: `python -m spiritvpn_bot bot|api`."""

from __future__ import annotations

import asyncio
import sys

import uvicorn

from spiritvpn_bot.di import build_container


def _run_bot() -> None:
    from spiritvpn_bot.presentation.telegram_bot.app import run_bot

    async def _main() -> None:
        container = build_container()
        await run_bot(container)

    asyncio.run(_main())


def _run_api() -> None:
    from spiritvpn_bot.presentation.mini_app_api.main import create_app

    async def _main() -> None:
        container = build_container()
        app = create_app(
            get_my_links=container.get_my_links_use_case(),
            token_signer=container.token_signer,
            bot_token=container.settings.telegram_bot_token,
            subscription_base_url=container.settings.subscription_base_url,
            plans=container.plans,
        )
        config = uvicorn.Config(
            app,
            host="0.0.0.0",  # noqa: S104
            port=container.settings.mini_app_http_port,
        )
        await uvicorn.Server(config).serve()

    asyncio.run(_main())


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("bot", "api"):
        print("использование: python -m spiritvpn_bot bot|api", file=sys.stderr)
        sys.exit(2)

    if sys.argv[1] == "bot":
        _run_bot()
    else:
        _run_api()


if __name__ == "__main__":
    main()
