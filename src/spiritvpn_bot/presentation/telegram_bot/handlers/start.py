from __future__ import annotations

from collections.abc import Callable

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from spiritvpn_bot.application.errors import ExpiryRegression
from spiritvpn_bot.application.subscription_token import SubscriptionTokenSigner
from spiritvpn_bot.application.use_cases.redeem_friend_code import RedeemFriendCodeUseCase
from spiritvpn_bot.application.use_cases.request_vpn_access import RequestAccessUseCase
from spiritvpn_bot.logging import get_logger

logger = get_logger(__name__)

router = Router(name="start")

WELCOME_TEXT = (
    "Добро пожаловать в SpiritVPN!\n\nОткройте приложение, чтобы посмотреть тарифы и "
    "управлять подпиской."
)

FALLBACK_TEXT = "Не понимаю это сообщение. Откройте приложение кнопкой ниже — там весь функционал."


def mini_app_keyboard(mini_app_url: str) -> InlineKeyboardMarkup:
    """Кнопка на мини-апп."""
    button = (
        InlineKeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=mini_app_url))
        if mini_app_url.startswith("https://")
        else InlineKeyboardButton(text="Открыть приложение (dev, в браузере)", url=mini_app_url)
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


async def answer_with_mini_app(message: Message, text: str, mini_app_url: str) -> None:
    """Отправляет ответ с кнопкой на мини-апп.

    Args:
        message: сообщение, на которое отвечаем.
        text: текст ответа.
        mini_app_url: публичный URL мини-аппа для кнопки.
    """
    try:
        await message.answer(text, reply_markup=mini_app_keyboard(mini_app_url))
    except TelegramBadRequest as exc:
        if "HTTP URL" not in exc.message:
            raise
        logger.warning("mini_app_button_rejected", mini_app_url=mini_app_url, error=exc.message)
        await message.answer(f"{text}\n\n{mini_app_url}")


async def handle_start(message: Message, mini_app_url: str) -> None:
    """/start — приветствие и кнопка на мини-апп."""
    await answer_with_mini_app(message, WELCOME_TEXT, mini_app_url)


async def handle_text(
    message: Message,
    redeem_friend_code_factory: Callable[[], RedeemFriendCodeUseCase],
    request_access_factory: Callable[[], RequestAccessUseCase],
    token_signer: SubscriptionTokenSigner,
    subscription_base_url: str,
    mini_app_url: str,
) -> None:
    """Любое обычное сообщение (не команда) — проверка пароля(если это free план) и выдача подписки.

    Args:
        message: входящее сообщение.
        redeem_friend_code_factory: фабрика use case проверки пароля.
        request_access_factory: фабрика use case запроса доступа у spiritvpnd.
        token_signer: подпись токена подписочной ссылки.
        subscription_base_url: публичный базовый URL для /s/{token}.
        mini_app_url: публичный URL мини-аппа для кнопки.
    """
    assert message.from_user is not None
    assert message.text is not None
    customer_id = f"tg:{message.from_user.id}"

    order = await redeem_friend_code_factory().execute(
        customer_id=customer_id, submitted_code=message.text
    )
    if order is None:
        await answer_with_mini_app(message, FALLBACK_TEXT, mini_app_url)
        return

    try:
        await request_access_factory().execute(order_id=order.id)
    except ExpiryRegression:
        logger.warning(
            "request_access_expiry_regression", order_id=order.id, customer_id=customer_id
        )
        await answer_with_mini_app(
            message,
            "Текущий срок доступа длиннее того, что даёт этот код — бэк сервис SpiritVPN не "
            "укорачивает подписку. Возьмите код с бо́льшим сроком либо дождитесь "
            "истечения текущего.",
            mini_app_url,
        )
        return
    except Exception:
        logger.exception("request_access_failed", order_id=order.id, customer_id=customer_id)
        await answer_with_mini_app(
            message,
            "Доступ оформлен, но не получилось прямо сейчас связаться с сервером "
            "VPN — загляните в приложение чуть позже.",
            mini_app_url,
        )
        return

    token = token_signer.sign(customer_id)
    await answer_with_mini_app(
        message,
        "Готово! Активируем доступ, обычно 5–30 секунд.\n\n"
        f"Ссылка подписки:\n{subscription_base_url}/s/{token}\n\n"
        "Вставьте её в любой VLESS-клиент (v2rayNG, Hiddify, Streisand и т. п.) "
        "как подписку — серверы появятся сами.",
        mini_app_url,
    )


router.message.register(handle_start, CommandStart())
router.message.register(handle_text, F.text & ~F.text.startswith("/"))
