"""Временная точка входа.

aiogram-хендлеры и FastAPI-приложение mini app ещё не собраны — см. README,
раздел «Статус». Модуль существует, чтобы Dockerfile мог собрать рабочий
образ и CI/CD гонял настоящий build+push с первого коммита, а не с момента,
когда бот доедет до готовности. Замените на реальный запуск aiogram, когда
появятся хендлеры в presentation/telegram_bot/handlers.
"""

from __future__ import annotations

import sys


def main() -> None:
    print(
        "spiritvpn-bot: entrypoint-заглушка, handlers ещё не собраны",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
