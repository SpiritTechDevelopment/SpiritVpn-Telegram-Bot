from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from spiritvpn_bot.application.errors import ExpiryRegression
from spiritvpn_bot.application.plans import PlanCatalog
from spiritvpn_bot.application.subscription_token import SubscriptionTokenSigner
from spiritvpn_bot.application.use_cases.get_my_links import GetMyLinksUseCase
from spiritvpn_bot.application.use_cases.get_subscription_status import (
    GetSubscriptionStatusUseCase,
)
from spiritvpn_bot.application.use_cases.redeem_friend_code import RedeemFriendCodeUseCase
from spiritvpn_bot.application.use_cases.request_vpn_access import RequestAccessUseCase
from spiritvpn_bot.logging import get_logger

logger = get_logger(__name__)

router = Router(name="start")

WELCOME_VIDEO_PATH = Path(__file__).resolve().parent.parent / "assets" / "welcome.mp4"

WELCOME_CAPTION = (
    "SpiritVPN — VPN на основе VLESS + REALITY: трафик неотличим от обычного HTTPS, "
    "для провайдера это просто открытый сайт.\n\n"
    "Выделенные серверы в нескольких странах, быстрая скорость и мгновенная "
    "активация.\n\n"
    "Подписка — от 100 ₽/мес.\n\n"
    "Откройте приложение, чтобы выбрать тариф и получить свои VPN серверы. 🚀"
)

FALLBACK_TEXT = "Не понимаю это сообщение. Откройте приложение кнопкой ниже — там весь функционал."

HELP_TEXT = (
    "Команды SpiritVPN:\n\n"
    "🚀 /start — приветствие и кнопки\n"
    "📊 /status — статус подписки и серверов\n"
    "💳 /plans — доступные тарифы\n"
    "🆘 /support — связаться с поддержкой\n"
    "❓ /help — это сообщение"
)

_welcome_video_file_id: str | None = None


def _mini_app_button(mini_app_url: str) -> InlineKeyboardButton:
    return (
        InlineKeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=mini_app_url))
        if mini_app_url.startswith("https://")
        else InlineKeyboardButton(text="Открыть приложение (dev, в браузере)", url=mini_app_url)
    )


def mini_app_keyboard(mini_app_url: str) -> InlineKeyboardMarkup:
    """Кнопка на мини-апп."""
    return InlineKeyboardMarkup(inline_keyboard=[[_mini_app_button(mini_app_url)]])


def welcome_keyboard(mini_app_url: str, support_url: str, reviews_url: str) -> InlineKeyboardMarkup:
    """Кнопки приветственного сообщения: приложение, поддержка, отзывы.
    mini_app_url: публичный URL мини-аппа для кнопки.
    support_url: публичный URL поддержки для кнопки.
    reviews_url: публичный URL отзывов для кнопки.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_mini_app_button(mini_app_url)],
            [InlineKeyboardButton(text="Поддержка 24/7", url=support_url)],
            [InlineKeyboardButton(text="Отзывы", url=reviews_url)],
        ]
    )


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


async def _send_welcome_video(
    message: Message, caption: str, reply_markup: InlineKeyboardMarkup | None
) -> None:
    global _welcome_video_file_id
    video = _welcome_video_file_id or FSInputFile(WELCOME_VIDEO_PATH)
    sent = await message.answer_video(video, caption=caption, reply_markup=reply_markup)
    if _welcome_video_file_id is None and sent.video is not None:
        _welcome_video_file_id = sent.video.file_id


async def handle_start(
    message: Message, mini_app_url: str, support_url: str, reviews_url: str
) -> None:
    """/start — приветственное видео и кнопки (приложение, поддержка, отзывы)."""
    try:
        await _send_welcome_video(
            message, WELCOME_CAPTION, welcome_keyboard(mini_app_url, support_url, reviews_url)
        )
    except TelegramBadRequest as exc:
        if "HTTP URL" not in exc.message:
            raise
        logger.warning("mini_app_button_rejected", mini_app_url=mini_app_url, error=exc.message)
        fallback_caption = (
            f"{WELCOME_CAPTION}\n\n"
            f"Приложение: {mini_app_url}\n"
            f"Поддержка: {support_url}\n"
            f"Отзывы: {reviews_url}"
        )
        await _send_welcome_video(message, fallback_caption, None)


def _days_word(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "день"
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return "дня"
    return "дней"


async def handle_status(
    message: Message,
    get_subscription_status_factory: Callable[[], GetSubscriptionStatusUseCase],
    get_my_links_factory: Callable[[], GetMyLinksUseCase],
    mini_app_url: str,
) -> None:
    """/status — краткая сводка по подписке и серверам."""
    assert message.from_user is not None
    customer_id = f"tg:{message.from_user.id}"

    days_left = await get_subscription_status_factory().execute(customer_id=customer_id)

    if days_left is None:
        await answer_with_mini_app(
            message,
            "🔒 Подписка не активна. Откройте приложение, чтобы выбрать тариф.",
            mini_app_url,
        )
        return

    links = await get_my_links_factory().execute(customer_id=customer_id)
    ready = sum(1 for link in links if link.state == "READY")
    total = len(links)
    servers_line = f"Серверы: {ready}/{total} активны" if total else "Серверы ещё не выданы"

    if days_left > 0:
        text = f"✅ Подписка активна: осталось {days_left} {_days_word(days_left)}.\n{servers_line}"
    else:
        text = f"⏳ Подписка истекла.\n{servers_line}\n\nПродлите её в приложении."

    await answer_with_mini_app(message, text, mini_app_url)


async def handle_plans(message: Message, plans: PlanCatalog, mini_app_url: str) -> None:
    """/plans — список доступных тарифов.
    Args:
        message: входящее сообщение.
        plans: каталог тарифов.
        mini_app_url: публичный URL мини-аппа для кнопки.
    """
    lines = ["💳 Тарифы SpiritVPN:", ""]
    for plan in plans.purchasable():
        quota = "безлимит" if plan.display_as_unlimited else f"{plan.quota_bytes // (1024**3)} ГБ"
        price = plan.price.amount_minor // 100
        lines.append(f"• {plan.title} — {quota} · {price} ₽")
    lines.append("")
    lines.append("Оформить можно в приложении.")
    await answer_with_mini_app(message, "\n".join(lines), mini_app_url)


async def handle_support(message: Message, support_url: str) -> None:
    """/support — прямая ссылка на поддержку 24/7.
    Args:
        message: входящее сообщение.
        support_url: публичный URL поддержки для кнопки.
    """
    await message.answer(
        "🆘 Поддержка на связи 24/7:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Написать в поддержку", url=support_url)]]
        ),
    )


async def handle_help(message: Message, mini_app_url: str) -> None:
    """/help — список команд.
    Args:
        message: входящее сообщение.
        mini_app_url: публичный URL мини-аппа для кнопки.
    """
    await answer_with_mini_app(message, HELP_TEXT, mini_app_url)


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
        "Готово! Активируем доступ...\n\n"
        f"Ссылка подписки:\n{subscription_base_url}/s/{token}\n\n"
        "Вставьте её в любой VLESS-клиент (v2rayNG, Hiddify, Streisand и т. п.) "
        "как подписку — серверы появятся сами.",
        mini_app_url,
    )


router.message.register(handle_start, CommandStart())
router.message.register(handle_status, Command("status"))
router.message.register(handle_plans, Command("plans"))
router.message.register(handle_support, Command("support"))
router.message.register(handle_help, Command("help"))
router.message.register(handle_text, F.text & ~F.text.startswith("/"))
