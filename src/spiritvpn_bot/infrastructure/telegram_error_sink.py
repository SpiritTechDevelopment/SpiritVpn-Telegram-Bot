from __future__ import annotations

from aiogram import Bot

_MAX_TELEGRAM_MESSAGE_LENGTH = 4000


class TelegramErrorSink:
    """Пересылает текст ошибки в топик Telegram чата."""

    def __init__(self, *, bot: Bot, chat_id: str, message_thread_id: int | None) -> None:
        self._bot = bot
        self._chat_id = chat_id
        self._message_thread_id = message_thread_id

    async def send(self, text: str) -> None:
        """Отправляет текст в ошибки чат Telegram, обрезая до 4000 символов.

        Args:
            text (str): Текст ошибки для отправки в Telegram.
        """
        await self._bot.send_message(
            chat_id=self._chat_id,
            text=text[:_MAX_TELEGRAM_MESSAGE_LENGTH],
            message_thread_id=self._message_thread_id,
        )
