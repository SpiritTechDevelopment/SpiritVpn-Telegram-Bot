from __future__ import annotations

import re
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
from spiritvpn_bot.application.use_cases.create_dev_access_link import CreateDevAccessLinkUseCase
from spiritvpn_bot.application.use_cases.get_my_links import GetMyLinksUseCase
from spiritvpn_bot.application.use_cases.get_subscription_status import (
    GetSubscriptionStatusUseCase,
)
from spiritvpn_bot.application.use_cases.redeem_friend_code import RedeemFriendCodeUseCase
from spiritvpn_bot.application.use_cases.request_vpn_access import RequestAccessUseCase
from spiritvpn_bot.logging import get_logger
from spiritvpn_bot.presentation.telegram_bot import texts

logger = get_logger(__name__)

router = Router(name="start")

WELCOME_ANIMATION_PATH = Path(__file__).resolve().parent.parent / "assets" / "welcome.mp4"

_welcome_animation_file_id: str | None = None

_DEV_CREATE_LINK_RE = re.compile(r"^create_(\d+)_(\d+)$")


def _mini_app_button(mini_app_url: str) -> InlineKeyboardButton:
    return (
        InlineKeyboardButton(text=texts.BTN_OPEN_APP, web_app=WebAppInfo(url=mini_app_url))
        if mini_app_url.startswith("https://")
        else InlineKeyboardButton(text=texts.BTN_OPEN_APP_DEV, url=mini_app_url)
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
            [InlineKeyboardButton(text=texts.BTN_SUPPORT, url=support_url)],
            [InlineKeyboardButton(text=texts.BTN_REVIEWS, url=reviews_url)],
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
    global _welcome_animation_file_id
    animation = _welcome_animation_file_id or FSInputFile(WELCOME_ANIMATION_PATH)
    sent = await message.answer_animation(animation, caption=caption, reply_markup=reply_markup)
    if _welcome_animation_file_id is None and sent.animation is not None:
        _welcome_animation_file_id = sent.animation.file_id


async def handle_start(
    message: Message, mini_app_url: str, support_url: str, reviews_url: str
) -> None:
    """/start — приветственное видео и кнопки (приложение, поддержка, отзывы)."""
    try:
        await _send_welcome_video(
            message, texts.WELCOME_CAPTION, welcome_keyboard(mini_app_url, support_url, reviews_url)
        )
    except TelegramBadRequest as exc:
        if "HTTP URL" not in exc.message:
            raise
        logger.warning("mini_app_button_rejected", mini_app_url=mini_app_url, error=exc.message)
        fallback_caption = texts.WELCOME_FALLBACK_TEMPLATE.format(
            caption=texts.WELCOME_CAPTION,
            mini_app_url=mini_app_url,
            support_url=support_url,
            reviews_url=reviews_url,
        )
        await _send_welcome_video(message, fallback_caption, None)


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
        await answer_with_mini_app(message, texts.STATUS_NO_SUBSCRIPTION, mini_app_url)
        return

    links = await get_my_links_factory().execute(customer_id=customer_id)
    ready = sum(1 for link in links if link.state == "READY")
    total = len(links)
    servers_line = (
        texts.STATUS_SERVERS_READY_TEMPLATE.format(ready=ready, total=total)
        if total
        else texts.STATUS_SERVERS_NONE
    )

    if days_left > 0:
        text = texts.STATUS_ACTIVE_TEMPLATE.format(
            days=days_left, days_word=texts.days_word(days_left), servers_line=servers_line
        )
    else:
        text = texts.STATUS_EXPIRED_TEMPLATE.format(servers_line=servers_line)

    await answer_with_mini_app(message, text, mini_app_url)


async def handle_plans(
    message: Message,
    get_subscription_status_factory: Callable[[], GetSubscriptionStatusUseCase],
    plans: PlanCatalog,
    mini_app_url: str,
) -> None:
    """/plans — тарифы, доступные регионы и текущий статус подписки.
    Args:
        message: входящее сообщение.
        get_subscription_status_factory: фабрика use case статуса подписки.
        plans: каталог тарифов.
        mini_app_url: публичный URL мини-аппа для кнопки.
    """
    assert message.from_user is not None
    customer_id = f"tg:{message.from_user.id}"
    days_left = await get_subscription_status_factory().execute(customer_id=customer_id)

    lines = [texts.PLANS_HEADER, ""]
    if days_left is None:
        lines.append(texts.PLANS_STATUS_NONE)
    elif days_left > 0:
        lines.append(
            texts.PLANS_STATUS_ACTIVE_TEMPLATE.format(
                days=days_left, days_word=texts.days_word(days_left)
            )
        )
    else:
        lines.append(texts.PLANS_STATUS_EXPIRED)
    lines.append("")

    for plan in plans.purchasable():
        quota = "безлимит" if plan.display_as_unlimited else f"{plan.quota_bytes // (1024**3)} ГБ"
        price = plan.price.amount_minor // 100
        lines.append(texts.PLANS_LINE_TEMPLATE.format(title=plan.title, quota=quota, price=price))
    lines.append("")

    lines.append(texts.PLANS_REGIONS_HEADER)
    lines.append("")
    lines.append(texts.PLANS_REGIONS_LIST)
    lines.append("")

    lines.append(texts.PLANS_FOOTER)
    await answer_with_mini_app(message, "\n".join(lines), mini_app_url)


async def handle_support(message: Message, support_url: str) -> None:
    """/support — прямая ссылка на поддержку 24/7.
    Args:
        message: входящее сообщение.
        support_url: публичный URL поддержки для кнопки.
    """
    await message.answer(
        texts.SUPPORT_HEADER,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=texts.BTN_SUPPORT_DIRECT, url=support_url)]]
        ),
    )


async def handle_reviews(message: Message, reviews_url: str) -> None:
    """/reviews — прямая ссылка на отзывы о SpiritVPN.
    Args:
        message: входящее сообщение.
        reviews_url: публичный URL канала с отзывами для кнопки.
    """
    await message.answer(
        texts.REVIEWS_HEADER,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=texts.BTN_REVIEWS_DIRECT, url=reviews_url)]]
        ),
    )


async def handle_help(message: Message, mini_app_url: str) -> None:
    """/help — список команд.
    Args:
        message: входящее сообщение.
        mini_app_url: публичный URL мини-аппа для кнопки.
    """
    await answer_with_mini_app(message, texts.HELP_TEXT, mini_app_url)


async def _handle_dev_create_link(
    message: Message,
    use_case: CreateDevAccessLinkUseCase,
    minutes: int,
    num_bytes: int,
) -> None:
    assert message.from_user is not None
    logger.info(
        "dev_create_link_invoked",
        source="bot",
        requested_by=message.from_user.id,
        minutes=minutes,
        num_bytes=num_bytes,
    )
    customer_id, links = await use_case.execute(minutes=minutes, num_bytes=num_bytes)
    header = f"customer_id: {customer_id}\nминуты: {minutes}, байты: {num_bytes}"
    if links is None:
        await message.answer(f"{header}\nСсылка не готова за отведённое время.")
        return
    uris = "\n".join(link.uri for link in links if link.uri)
    await message.answer(f"{header}\n\n{uris}")


async def handle_text(
    message: Message,
    redeem_friend_code_factory: Callable[[], RedeemFriendCodeUseCase],
    request_access_factory: Callable[[], RequestAccessUseCase],
    token_signer: SubscriptionTokenSigner,
    subscription_base_url: str,
    mini_app_url: str,
    dev_admin_user_ids: frozenset[int],
    dev_create_link_use_case: CreateDevAccessLinkUseCase,
) -> None:
    """Любое обычное сообщение (не команда) — проверка пароля(если это free план) и выдача подписки.

    Строго распознаёт create_<минуты>_<байты> для админов из dev_admin_user_ids
    (см. CreateDevAccessLinkUseCase) — и только для них, чтобы паттерн нельзя
    было угадать/перебрать: для всех остальных (не тот формат, не тот
    отправитель) сообщение падает в обычный флоу ниже, без каких-либо отличий
    в поведении.

    Args:
        message: входящее сообщение.
        redeem_friend_code_factory: фабрика use case проверки пароля.
        request_access_factory: фабрика use case запроса доступа у spiritvpnd.
        token_signer: подпись токена подписочной ссылки.
        subscription_base_url: публичный базовый URL для /s/{token}.
        mini_app_url: публичный URL мини-аппа для кнопки.
        dev_admin_user_ids: id, кому доступна create_<минуты>_<байты>.
        dev_create_link_use_case: use case выдачи dev-доступа.
    """
    assert message.from_user is not None
    assert message.text is not None

    dev_match = _DEV_CREATE_LINK_RE.match(message.text.strip())
    if dev_match and message.from_user.id in dev_admin_user_ids:
        await _handle_dev_create_link(
            message,
            dev_create_link_use_case,
            int(dev_match.group(1)),
            int(dev_match.group(2)),
        )
        return

    customer_id = f"tg:{message.from_user.id}"

    order = await redeem_friend_code_factory().execute(
        customer_id=customer_id, submitted_code=message.text
    )
    if order is None:
        await answer_with_mini_app(message, texts.FALLBACK_TEXT, mini_app_url)
        return

    try:
        await request_access_factory().execute(order_id=order.id)
    except ExpiryRegression:
        logger.warning(
            "request_access_expiry_regression", order_id=order.id, customer_id=customer_id
        )
        await answer_with_mini_app(message, texts.TEXT_EXPIRY_REGRESSION, mini_app_url)
        return
    except Exception:
        logger.exception("request_access_failed", order_id=order.id, customer_id=customer_id)
        await answer_with_mini_app(message, texts.TEXT_ACCESS_REQUEST_FAILED, mini_app_url)
        return

    token = token_signer.sign(customer_id)
    subscription_url = f"{subscription_base_url}/s/{token}"
    await answer_with_mini_app(
        message,
        texts.TEXT_ACCESS_GRANTED_TEMPLATE.format(subscription_url=subscription_url),
        mini_app_url,
    )


router.message.register(handle_start, CommandStart())
router.message.register(handle_status, Command("status"))
router.message.register(handle_plans, Command("plans"))
router.message.register(handle_support, Command("support"))
router.message.register(handle_reviews, Command("reviews"))
router.message.register(handle_help, Command("help"))
router.message.register(handle_text, F.text & ~F.text.startswith("/"))
