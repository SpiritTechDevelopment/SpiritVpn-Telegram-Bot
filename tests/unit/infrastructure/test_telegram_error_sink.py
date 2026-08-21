from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from spiritvpn_bot.infrastructure.telegram_error_sink import TelegramErrorSink


@dataclass
class FakeBot:
    """Фекйовый aiogram.Bot: send() трогает только send_message."""

    calls: list[dict[str, Any]] = field(default_factory=list)

    async def send_message(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)


async def test_send_forwards_chat_and_thread_id() -> None:
    bot = FakeBot()
    sink = TelegramErrorSink(bot=bot, chat_id="-100123", message_thread_id=18)  # type: ignore[arg-type]

    await sink.send("boom")

    assert len(bot.calls) == 1
    assert bot.calls[0]["chat_id"] == "-100123"
    assert bot.calls[0]["message_thread_id"] == 18
    assert bot.calls[0]["text"] == "boom"


async def test_send_truncates_very_long_text() -> None:
    bot = FakeBot()
    sink = TelegramErrorSink(bot=bot, chat_id="-100123", message_thread_id=None)  # type: ignore[arg-type]

    await sink.send("x" * 5000)

    assert len(bot.calls[0]["text"]) <= 4000
