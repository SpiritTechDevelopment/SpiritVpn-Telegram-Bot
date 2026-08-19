from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from aiogram.exceptions import TelegramBadRequest

from spiritvpn_bot.application.plans import build_plan_catalog
from spiritvpn_bot.application.subscription_token import SubscriptionTokenSigner
from spiritvpn_bot.application.use_cases.redeem_friend_code import RedeemFriendCodeUseCase
from spiritvpn_bot.application.use_cases.request_vpn_access import RequestAccessUseCase
from spiritvpn_bot.presentation.telegram_bot.handlers.start import handle_start, handle_text
from tests.unit.application.fakes import (
    FakeClock,
    FakeEventPublisher,
    FakeIdGenerator,
    FakeUnitOfWork,
    FakeVPNAccessGateway,
    InMemoryCommandSequenceRepository,
    InMemoryOrderRepository,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
PLANS = build_plan_catalog(friends_fleet_id=1, friends_quota_bytes=10, friends_duration_days=30)
SUBSCRIPTION_BASE_URL = "https://sub.example.test"
MINI_APP_URL = "https://app.example.test"
SIGNING_KEY = b"test-signing-key"
SHARED_CODE = "letmein"


@dataclass
class FakeUser:
    id: int


@dataclass
class FakeAnswer:
    text: str
    reply_markup: Any = None


@dataclass
class FakeMessage:
    """Двойник aiogram.types.Message: хендлер трогает только from_user,
    text и answer(), настоящий Bot/сессия для теста не нужны."""

    from_user: FakeUser
    text: str | None = None
    answers: list[FakeAnswer] = field(default_factory=list)
    reject_button_urls: bool = False

    async def answer(self, text: str, reply_markup: Any = None) -> None:
        if reply_markup is not None and self.reject_button_urls:
            raise TelegramBadRequest(
                method=None,  # type: ignore[arg-type]
                message=(
                    "Bad Request: inline keyboard button URL 'http://localhost:8081' "
                    "is invalid: Wrong HTTP URL"
                ),
            )
        self.answers.append(FakeAnswer(text, reply_markup))


def build_use_cases() -> (
    tuple[FakeUnitOfWork, FakeVPNAccessGateway, RedeemFriendCodeUseCase, RequestAccessUseCase]
):
    uow = FakeUnitOfWork(InMemoryOrderRepository(), InMemoryCommandSequenceRepository())
    gateway = FakeVPNAccessGateway()
    redeem = RedeemFriendCodeUseCase(
        uow, FakeIdGenerator(), FakeClock(NOW), FakeEventPublisher(), PLANS, SHARED_CODE
    )
    request_access = RequestAccessUseCase(uow, gateway, FakeEventPublisher())
    return uow, gateway, redeem, request_access


async def test_start_shows_welcome_and_mini_app_button() -> None:
    message = FakeMessage(from_user=FakeUser(id=1))

    await handle_start(message, MINI_APP_URL)  # type: ignore[arg-type]

    assert len(message.answers) == 1
    assert "SpiritVPN" in message.answers[0].text
    assert "пароль" not in message.answers[0].text.lower()
    assert "код" not in message.answers[0].text.lower()
    assert message.answers[0].reply_markup is not None


async def test_correct_shared_code_grants_access() -> None:
    uow, gateway, redeem, request_access = build_use_cases()
    signer = SubscriptionTokenSigner(SIGNING_KEY)
    message = FakeMessage(from_user=FakeUser(id=42), text=SHARED_CODE)

    await handle_text(
        message,  # type: ignore[arg-type]
        lambda: redeem,
        lambda: request_access,
        signer,
        SUBSCRIPTION_BASE_URL,
        MINI_APP_URL,
    )

    assert len(message.answers) == 1
    assert "Готово" in message.answers[0].text
    assert f"{SUBSCRIPTION_BASE_URL}/s/" in message.answers[0].text
    assert len(gateway.applied) == 1
    assert gateway.applied[0].customer_id == "tg:42"
    assert gateway.applied[0].fleet_id == 1


async def test_wrong_text_gets_generic_fallback_not_mentioning_a_code() -> None:
    uow, gateway, redeem, request_access = build_use_cases()
    signer = SubscriptionTokenSigner(SIGNING_KEY)
    message = FakeMessage(from_user=FakeUser(id=42), text="привет")

    await handle_text(
        message,  # type: ignore[arg-type]
        lambda: redeem,
        lambda: request_access,
        signer,
        SUBSCRIPTION_BASE_URL,
        MINI_APP_URL,
    )

    assert len(message.answers) == 1
    reply = message.answers[0].text.lower()
    assert "пароль" not in reply
    assert "код" not in reply
    assert gateway.applied == []


async def test_wrong_code_and_random_text_get_identical_reply() -> None:
    # несовпадение пароля не должно быть отличимо от любого другого
    # непонятного сообщения — иначе перебором можно нащупать, что он есть
    uow, gateway, redeem, request_access = build_use_cases()
    signer = SubscriptionTokenSigner(SIGNING_KEY)
    args = (lambda: redeem, lambda: request_access, signer, SUBSCRIPTION_BASE_URL, MINI_APP_URL)

    almost_right = FakeMessage(from_user=FakeUser(id=1), text=SHARED_CODE + "x")
    random_text = FakeMessage(from_user=FakeUser(id=2), text="какой-то текст")

    await handle_text(almost_right, *args)  # type: ignore[arg-type]
    await handle_text(random_text, *args)  # type: ignore[arg-type]

    assert almost_right.answers[0].text == random_text.answers[0].text


async def test_shared_code_can_be_reused_by_anyone_who_knows_it() -> None:
    # не персональный код: второй пользователь с тем же паролем тоже получает доступ
    uow, gateway, redeem, request_access = build_use_cases()
    signer = SubscriptionTokenSigner(SIGNING_KEY)
    args = (lambda: redeem, lambda: request_access, signer, SUBSCRIPTION_BASE_URL, MINI_APP_URL)

    first = FakeMessage(from_user=FakeUser(id=1), text=SHARED_CODE)
    second = FakeMessage(from_user=FakeUser(id=2), text=SHARED_CODE)

    await handle_text(first, *args)  # type: ignore[arg-type]
    await handle_text(second, *args)  # type: ignore[arg-type]

    assert "Готово" in first.answers[0].text
    assert "Готово" in second.answers[0].text
    assert len(gateway.applied) == 2


async def test_rejected_button_url_falls_back_to_plain_link() -> None:
    message = FakeMessage(from_user=FakeUser(id=1), reject_button_urls=True)

    await handle_start(message, "http://localhost:8081")  # type: ignore[arg-type]

    assert len(message.answers) == 1
    assert message.answers[0].reply_markup is None
    assert "http://localhost:8081" in message.answers[0].text
    assert "SpiritVPN" in message.answers[0].text


async def test_gateway_failure_after_match_still_replies() -> None:
    uow, gateway, redeem, request_access = build_use_cases()
    gateway.raise_on_apply = ConnectionError("spiritvpnd unreachable")
    signer = SubscriptionTokenSigner(SIGNING_KEY)
    message = FakeMessage(from_user=FakeUser(id=42), text=SHARED_CODE)

    await handle_text(
        message,  # type: ignore[arg-type]
        lambda: redeem,
        lambda: request_access,
        signer,
        SUBSCRIPTION_BASE_URL,
        MINI_APP_URL,
    )

    assert len(message.answers) == 1
    assert "оформлен" in message.answers[0].text
