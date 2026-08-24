from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

from aiogram.exceptions import TelegramBadRequest

from spiritvpn_bot.application.errors import ExpiryRegression
from spiritvpn_bot.application.plans import build_plan_catalog
from spiritvpn_bot.application.ports.vpn_gateway import AccessLink
from spiritvpn_bot.application.subscription_token import SubscriptionTokenSigner
from spiritvpn_bot.application.use_cases.create_dev_access_link import CreateDevAccessLinkUseCase
from spiritvpn_bot.application.use_cases.get_my_links import GetMyLinksUseCase
from spiritvpn_bot.application.use_cases.get_subscription_status import (
    GetSubscriptionStatusUseCase,
)
from spiritvpn_bot.application.use_cases.redeem_friend_code import RedeemFriendCodeUseCase
from spiritvpn_bot.application.use_cases.request_vpn_access import RequestAccessUseCase
from spiritvpn_bot.domain.entities.money import Money
from spiritvpn_bot.domain.entities.order import Order, OrderStatus
from spiritvpn_bot.domain.entities.plan import Plan
from spiritvpn_bot.presentation.telegram_bot.handlers.start import (
    handle_help,
    handle_plans,
    handle_start,
    handle_status,
    handle_support,
    handle_text,
)
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
SUPPORT_URL = "https://t.me/support_test"
REVIEWS_URL = "https://t.me/reviews_test"
SIGNING_KEY = b"test-signing-key"
SHARED_CODE = "letmein"

DEV_FLEET_ID = 1
DEV_ADMIN_ID = 999
DEV_ADMIN_IDS = frozenset({DEV_ADMIN_ID})
# ни один тест ниже, кроме dev_create_link-тестов, не должен реально дёргать
# use case — dev_admin_user_ids у них всегда пустой/чужой, так что это
# просто заглушка под сигнатуру handle_text.
DUMMY_DEV_USE_CASE = CreateDevAccessLinkUseCase(
    FakeVPNAccessGateway(), DEV_FLEET_ID, max_attempts=1, poll_interval_seconds=0
)


@dataclass
class FakeUser:
    id: int


@dataclass
class FakeAnswer:
    text: str
    reply_markup: Any = None


@dataclass
class FakeVideoAnswer:
    video: Any
    caption: str
    reply_markup: Any = None


@dataclass
class FakeMessage:
    """Двойник aiogram.types.Message: хендлер трогает только from_user,
    text, answer() и answer_video(), настоящий Bot/сессия для теста не нужны."""

    from_user: FakeUser
    text: str | None = None
    answers: list[FakeAnswer] = field(default_factory=list)
    video_answers: list[FakeVideoAnswer] = field(default_factory=list)
    reject_button_urls: bool = False

    async def answer(self, text: str, reply_markup: Any = None) -> None:
        if reply_markup is not None and self.reject_button_urls:
            raise self._button_rejected()
        self.answers.append(FakeAnswer(text, reply_markup))

    async def answer_video(
        self, video: Any, caption: str = "", reply_markup: Any = None
    ) -> SimpleNamespace:
        if reply_markup is not None and self.reject_button_urls:
            raise self._button_rejected()
        self.video_answers.append(FakeVideoAnswer(video, caption, reply_markup))
        return SimpleNamespace(video=None)

    @staticmethod
    def _button_rejected() -> TelegramBadRequest:
        return TelegramBadRequest(
            method=None,  # type: ignore[arg-type]
            message=(
                "Bad Request: inline keyboard button URL 'http://localhost:8081' "
                "is invalid: Wrong HTTP URL"
            ),
        )


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


async def test_start_shows_welcome_video_and_buttons() -> None:
    message = FakeMessage(from_user=FakeUser(id=1))

    await handle_start(message, MINI_APP_URL, SUPPORT_URL, REVIEWS_URL)  # type: ignore[arg-type]

    assert len(message.video_answers) == 1
    assert len(message.answers) == 0
    video_answer = message.video_answers[0]
    assert "SpiritVPN" in video_answer.caption
    assert "пароль" not in video_answer.caption.lower()
    assert "код" not in video_answer.caption.lower()
    assert video_answer.reply_markup is not None
    assert len(video_answer.reply_markup.inline_keyboard) == 3


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
        DEV_ADMIN_IDS,
        DUMMY_DEV_USE_CASE,
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
        DEV_ADMIN_IDS,
        DUMMY_DEV_USE_CASE,
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
    args = (
        lambda: redeem,
        lambda: request_access,
        signer,
        SUBSCRIPTION_BASE_URL,
        MINI_APP_URL,
        DEV_ADMIN_IDS,
        DUMMY_DEV_USE_CASE,
    )

    almost_right = FakeMessage(from_user=FakeUser(id=1), text=SHARED_CODE + "x")
    random_text = FakeMessage(from_user=FakeUser(id=2), text="какой-то текст")

    await handle_text(almost_right, *args)  # type: ignore[arg-type]
    await handle_text(random_text, *args)  # type: ignore[arg-type]

    assert almost_right.answers[0].text == random_text.answers[0].text


async def test_shared_code_can_be_reused_by_anyone_who_knows_it() -> None:
    # не персональный код: второй пользователь с тем же паролем тоже получает доступ
    uow, gateway, redeem, request_access = build_use_cases()
    signer = SubscriptionTokenSigner(SIGNING_KEY)
    args = (
        lambda: redeem,
        lambda: request_access,
        signer,
        SUBSCRIPTION_BASE_URL,
        MINI_APP_URL,
        DEV_ADMIN_IDS,
        DUMMY_DEV_USE_CASE,
    )

    first = FakeMessage(from_user=FakeUser(id=1), text=SHARED_CODE)
    second = FakeMessage(from_user=FakeUser(id=2), text=SHARED_CODE)

    await handle_text(first, *args)  # type: ignore[arg-type]
    await handle_text(second, *args)  # type: ignore[arg-type]

    assert "Готово" in first.answers[0].text
    assert "Готово" in second.answers[0].text
    assert len(gateway.applied) == 2


async def test_rejected_button_url_falls_back_to_video_with_plain_links() -> None:
    message = FakeMessage(from_user=FakeUser(id=1), reject_button_urls=True)

    await handle_start(  # type: ignore[arg-type]
        message, "http://localhost:8081", SUPPORT_URL, REVIEWS_URL
    )

    assert len(message.video_answers) == 1
    video_answer = message.video_answers[0]
    assert video_answer.reply_markup is None
    assert "http://localhost:8081" in video_answer.caption
    assert SUPPORT_URL in video_answer.caption
    assert REVIEWS_URL in video_answer.caption
    assert "SpiritVPN" in video_answer.caption


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
        DEV_ADMIN_IDS,
        DUMMY_DEV_USE_CASE,
    )

    assert len(message.answers) == 1
    assert "оформлен" in message.answers[0].text


async def test_expiry_regression_gets_a_specific_explanation() -> None:
    uow, gateway, redeem, request_access = build_use_cases()
    gateway.raise_on_apply = ExpiryRegression(
        "FAILED_PRECONDITION", "сокращение expires_at не поддерживается"
    )
    signer = SubscriptionTokenSigner(SIGNING_KEY)
    message = FakeMessage(from_user=FakeUser(id=42), text=SHARED_CODE)

    await handle_text(
        message,  # type: ignore[arg-type]
        lambda: redeem,
        lambda: request_access,
        signer,
        SUBSCRIPTION_BASE_URL,
        MINI_APP_URL,
        DEV_ADMIN_IDS,
        DUMMY_DEV_USE_CASE,
    )

    assert len(message.answers) == 1
    assert "не укорачивает подписку" in message.answers[0].text


def _paid_order(order_id: str, command_number: int, expires_at: datetime) -> Order:
    plan = Plan(
        id="nl-30d",
        title="Netherlands, 30 days",
        fleet_id=1,
        duration_days=30,
        quota_bytes=10,
        price=Money(0, "RUB"),
    )
    order = Order(
        id=order_id,
        customer_id="tg:1",
        plan=plan,
        price=plan.price,
        status=OrderStatus.CREATED,
        created_at=NOW,
    )
    order.mark_awaiting_payment()
    order.mark_paid(command_number=command_number, expires_at=expires_at, payment_reference="x")
    return order


async def test_status_with_no_orders_prompts_to_pick_a_plan() -> None:
    uow = FakeUnitOfWork(InMemoryOrderRepository(), InMemoryCommandSequenceRepository())
    status_use_case = GetSubscriptionStatusUseCase(uow, FakeClock(NOW))
    links_use_case = GetMyLinksUseCase(FakeVPNAccessGateway())
    message = FakeMessage(from_user=FakeUser(id=1))

    await handle_status(
        message,  # type: ignore[arg-type]
        lambda: status_use_case,
        lambda: links_use_case,
        MINI_APP_URL,
    )

    assert len(message.answers) == 1
    assert "тариф" in message.answers[0].text.lower()


async def test_status_shows_days_left_and_ready_servers() -> None:
    uow = FakeUnitOfWork(InMemoryOrderRepository(), InMemoryCommandSequenceRepository())
    await uow.orders.add(_paid_order("order-1", 1, NOW + timedelta(days=18)))
    gateway = FakeVPNAccessGateway()
    gateway.links_by_customer["tg:1"] = [
        AccessLink(kind="BRIDGE", state="READY"),
        AccessLink(kind="BRIDGE", state="READY"),
        AccessLink(kind="BRIDGE", state="PENDING"),
    ]
    status_use_case = GetSubscriptionStatusUseCase(uow, FakeClock(NOW))
    links_use_case = GetMyLinksUseCase(gateway)
    message = FakeMessage(from_user=FakeUser(id=1))

    await handle_status(
        message,  # type: ignore[arg-type]
        lambda: status_use_case,
        lambda: links_use_case,
        MINI_APP_URL,
    )

    text = message.answers[0].text
    assert "18 дн" in text
    assert "2/3" in text


async def test_status_shows_expired_and_prompts_renewal() -> None:
    uow = FakeUnitOfWork(InMemoryOrderRepository(), InMemoryCommandSequenceRepository())
    await uow.orders.add(_paid_order("order-1", 1, NOW - timedelta(days=2)))
    status_use_case = GetSubscriptionStatusUseCase(uow, FakeClock(NOW))
    links_use_case = GetMyLinksUseCase(FakeVPNAccessGateway())
    message = FakeMessage(from_user=FakeUser(id=1))

    await handle_status(
        message,  # type: ignore[arg-type]
        lambda: status_use_case,
        lambda: links_use_case,
        MINI_APP_URL,
    )

    text = message.answers[0].text.lower()
    assert "истекла" in text
    assert "продлите" in text


async def test_plans_lists_purchasable_plans_with_price() -> None:
    message = FakeMessage(from_user=FakeUser(id=1))

    await handle_plans(message, PLANS, MINI_APP_URL)  # type: ignore[arg-type]

    text = message.answers[0].text
    assert "1 месяц" in text
    assert "100 ₽" in text
    assert "3 месяца" in text
    assert "300 ₽" in text
    assert "своих" not in text.lower()


async def test_support_sends_direct_link_button() -> None:
    message = FakeMessage(from_user=FakeUser(id=1))

    await handle_support(message, SUPPORT_URL)  # type: ignore[arg-type]

    assert len(message.answers) == 1
    assert message.answers[0].reply_markup is not None
    button = message.answers[0].reply_markup.inline_keyboard[0][0]
    assert button.url == SUPPORT_URL


async def test_help_lists_all_commands() -> None:
    message = FakeMessage(from_user=FakeUser(id=1))

    await handle_help(message, MINI_APP_URL)  # type: ignore[arg-type]

    text = message.answers[0].text
    for command in ("/start", "/status", "/plans", "/support", "/help"):
        assert command in text


class _AnyCustomerGateway(FakeVPNAccessGateway):
    """Отдаёт один и тот же набор ссылок для любого customer_id — dev use case
    сам генерирует рандомный id, тест заранее его не знает."""

    def __init__(self, links: list[AccessLink]) -> None:
        super().__init__()
        self._links = links

    async def get_links(self, *, customer_id: str) -> list[AccessLink]:
        self.journal.append(f"get_links:{customer_id}")
        return self._links


async def test_dev_create_link_works_for_admin_with_strict_format() -> None:
    uow, _unused_gateway, redeem, request_access = build_use_cases()
    dev_gateway = _AnyCustomerGateway(
        [AccessLink(kind="BRIDGE", state="READY", uri="vless://dev-link")]
    )
    use_case = CreateDevAccessLinkUseCase(
        dev_gateway, DEV_FLEET_ID, max_attempts=1, poll_interval_seconds=0
    )
    signer = SubscriptionTokenSigner(SIGNING_KEY)
    message = FakeMessage(from_user=FakeUser(id=DEV_ADMIN_ID), text="create_15_1000")

    await handle_text(
        message,  # type: ignore[arg-type]
        lambda: redeem,
        lambda: request_access,
        signer,
        SUBSCRIPTION_BASE_URL,
        MINI_APP_URL,
        DEV_ADMIN_IDS,
        use_case,
    )

    assert len(message.answers) == 1
    reply = message.answers[0].text
    assert "vless://dev-link" in reply
    assert "минуты: 15" in reply
    assert "байты: 1000" in reply
    assert len(dev_gateway.applied) == 1
    assert dev_gateway.applied[0].fleet_id == DEV_FLEET_ID
    assert dev_gateway.applied[0].quota_bytes == 1000
    assert dev_gateway.applied[0].customer_id.startswith("dev:")


async def test_dev_create_link_ignored_for_non_admin_same_as_any_wrong_text() -> None:
    # угадавший формат, но не из списка админов, не должен получать отличимый
    # от обычного "непонятного текста" ответ — иначе формат легко нащупать
    uow, gateway, redeem, request_access = build_use_cases()
    signer = SubscriptionTokenSigner(SIGNING_KEY)
    args = (
        lambda: redeem,
        lambda: request_access,
        signer,
        SUBSCRIPTION_BASE_URL,
        MINI_APP_URL,
        DEV_ADMIN_IDS,
        DUMMY_DEV_USE_CASE,
    )

    non_admin_dev_format = FakeMessage(from_user=FakeUser(id=1), text="create_15_1000")
    random_text = FakeMessage(from_user=FakeUser(id=2), text="какой-то текст")

    await handle_text(non_admin_dev_format, *args)  # type: ignore[arg-type]
    await handle_text(random_text, *args)  # type: ignore[arg-type]

    assert non_admin_dev_format.answers[0].text == random_text.answers[0].text
    assert gateway.applied == []


async def test_dev_create_link_requires_exact_format_even_for_admin() -> None:
    uow, gateway, redeem, request_access = build_use_cases()
    signer = SubscriptionTokenSigner(SIGNING_KEY)
    args = (
        lambda: redeem,
        lambda: request_access,
        signer,
        SUBSCRIPTION_BASE_URL,
        MINI_APP_URL,
        DEV_ADMIN_IDS,
        DUMMY_DEV_USE_CASE,
    )

    almost_no_bytes = FakeMessage(from_user=FakeUser(id=DEV_ADMIN_ID), text="create_15")
    non_numeric = FakeMessage(from_user=FakeUser(id=DEV_ADMIN_ID), text="create_15_abc")
    with_prefix = FakeMessage(from_user=FakeUser(id=DEV_ADMIN_ID), text="please create_15_1000")

    for message in (almost_no_bytes, non_numeric, with_prefix):
        await handle_text(message, *args)  # type: ignore[arg-type]
        assert "vless://" not in message.answers[0].text


async def test_dev_create_link_reports_timeout_if_never_ready() -> None:
    dev_gateway = _AnyCustomerGateway([AccessLink(kind="BRIDGE", state="PENDING")])
    use_case = CreateDevAccessLinkUseCase(
        dev_gateway, DEV_FLEET_ID, max_attempts=1, poll_interval_seconds=0
    )
    uow, _unused_gateway, redeem, request_access = build_use_cases()
    signer = SubscriptionTokenSigner(SIGNING_KEY)
    message = FakeMessage(from_user=FakeUser(id=DEV_ADMIN_ID), text="create_1_1")

    await handle_text(
        message,  # type: ignore[arg-type]
        lambda: redeem,
        lambda: request_access,
        signer,
        SUBSCRIPTION_BASE_URL,
        MINI_APP_URL,
        DEV_ADMIN_IDS,
        use_case,
    )

    assert "не готова" in message.answers[0].text.lower()
