from __future__ import annotations

import base64
import time
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from spiritvpn_bot.application.plans import build_plan_catalog
from spiritvpn_bot.application.ports.vpn_gateway import AccessLink
from spiritvpn_bot.application.subscription_token import SubscriptionTokenSigner
from spiritvpn_bot.application.use_cases.get_my_links import GetMyLinksUseCase
from spiritvpn_bot.application.use_cases.get_subscription_status import (
    GetSubscriptionStatusUseCase,
)
from spiritvpn_bot.presentation.mini_app_api.main import create_app
from tests.unit.application.fakes import (
    FakeClock,
    FakeUnitOfWork,
    FakeVPNAccessGateway,
    InMemoryCommandSequenceRepository,
    InMemoryOrderRepository,
)
from tests.unit.presentation.mini_app_api.test_auth import BOT_TOKEN, sign_init_data, valid_fields

SUBSCRIPTION_BASE_URL = "https://sub.example.test"
SIGNING_KEY = b"test-signing-key"
NOW = datetime(2026, 1, 1, tzinfo=UTC)

PLANS = build_plan_catalog(friends_fleet_id=1, friends_quota_bytes=10, friends_duration_days=30)


def make_client(gateway: FakeVPNAccessGateway) -> TestClient:
    uow = FakeUnitOfWork(InMemoryOrderRepository(), InMemoryCommandSequenceRepository())
    app = create_app(
        get_my_links=GetMyLinksUseCase(gateway),
        get_subscription_status=lambda: GetSubscriptionStatusUseCase(uow, FakeClock(NOW)),
        token_signer=SubscriptionTokenSigner(SIGNING_KEY),
        bot_token=BOT_TOKEN,
        subscription_base_url=SUBSCRIPTION_BASE_URL,
        plans=PLANS,
    )
    return TestClient(app)


def test_health() -> None:
    client = make_client(FakeVPNAccessGateway())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_subscription_endpoint_returns_base64_of_ready_links() -> None:
    gateway = FakeVPNAccessGateway()
    gateway.links_by_customer["tg:42"] = [
        AccessLink(kind="BRIDGE", state="READY", uri="vless://x@nl.example.com:443#NL"),
        AccessLink(kind="BRIDGE", state="PENDING"),
    ]
    signer = SubscriptionTokenSigner(SIGNING_KEY)
    client = make_client(gateway)

    token = signer.sign("tg:42")
    response = client.get(f"/s/{token}")

    assert response.status_code == 200
    assert base64.b64decode(response.text) == b"vless://x@nl.example.com:443#NL"


def test_subscription_endpoint_rejects_forged_token() -> None:
    client = make_client(FakeVPNAccessGateway())

    response = client.get("/s/not-a-real-token")

    assert response.status_code == 404


def test_my_links_requires_init_data_header() -> None:
    client = make_client(FakeVPNAccessGateway())

    response = client.get("/api/me/links")

    assert response.status_code == 422  # заголовок обязателен


def test_my_links_rejects_forged_init_data() -> None:
    client = make_client(FakeVPNAccessGateway())

    response = client.get("/api/me/links", headers={"X-Telegram-Init-Data": "garbage"})

    assert response.status_code == 401


def test_my_links_returns_link_statuses_without_uri() -> None:
    gateway = FakeVPNAccessGateway()
    gateway.links_by_customer["tg:42"] = [
        AccessLink(kind="BRIDGE", state="READY", uri="vless://secret#Amsterdam"),
        AccessLink(kind="BRIDGE", state="BLOCKED", block_reason="TIME_EXPIRED"),
    ]
    client = make_client(gateway)
    init_data = sign_init_data(valid_fields(user_id=42))

    response = client.get("/api/me/links", headers={"X-Telegram-Init-Data": init_data})

    assert response.status_code == 200
    body = response.json()
    assert body == [
        {
            "state": "READY",
            "label": "Amsterdam",
            "block_reason": None,
        },
        {
            "state": "BLOCKED",
            "label": None,
            "block_reason": "TIME_EXPIRED",
        },
    ]
    assert "secret" not in response.text


def test_my_links_hides_freedom_kind() -> None:
    gateway = FakeVPNAccessGateway()
    gateway.links_by_customer["tg:42"] = [
        AccessLink(kind="FREEDOM", state="READY", uri="vless://freedom#Amsterdam"),
        AccessLink(kind="BRIDGE", state="READY", uri="vless://bridge#Amsterdam"),
    ]
    client = make_client(gateway)
    init_data = sign_init_data(valid_fields(user_id=42))

    response = client.get("/api/me/links", headers={"X-Telegram-Init-Data": init_data})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert "kind" not in body[0]


def test_my_subscription_url_matches_signed_token() -> None:
    client = make_client(FakeVPNAccessGateway())
    init_data = sign_init_data(valid_fields(user_id=42))
    signer = SubscriptionTokenSigner(SIGNING_KEY)

    response = client.get("/api/me/subscription-url", headers={"X-Telegram-Init-Data": init_data})

    assert response.status_code == 200
    url = response.json()["url"]
    assert url.startswith(f"{SUBSCRIPTION_BASE_URL}/s/")
    token = url.removeprefix(f"{SUBSCRIPTION_BASE_URL}/s/")
    assert signer.verify(token) == "tg:42"


def test_my_subscription_status_requires_init_data_header() -> None:
    client = make_client(FakeVPNAccessGateway())

    response = client.get("/api/me/subscription-status")

    assert response.status_code == 422


def test_my_subscription_status_returns_none_for_customer_without_orders() -> None:
    client = make_client(FakeVPNAccessGateway())
    init_data = sign_init_data(valid_fields(user_id=42))

    response = client.get(
        "/api/me/subscription-status", headers={"X-Telegram-Init-Data": init_data}
    )

    assert response.status_code == 200
    assert response.json() == {"days_left": None}


def test_static_index_page_is_served() -> None:
    client = make_client(FakeVPNAccessGateway())

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "SpiritVPN" in response.text


def test_static_index_page_is_not_cached() -> None:
    client = make_client(FakeVPNAccessGateway())

    response = client.get("/")

    assert response.headers["cache-control"] == "no-store"


def test_plans_endpoint_hides_the_internal_friends_plan() -> None:
    # friends-free существует в каталоге, но не должен светиться в
    # публичной витрине мини-аппа — это не для клиентов
    client = make_client(FakeVPNAccessGateway())

    response = client.get("/api/plans")

    assert response.status_code == 200
    assert "friends-free" not in {plan["id"] for plan in response.json()}


def test_plans_endpoint_requires_no_auth() -> None:
    # каталог цен — не персональные данные
    client = make_client(FakeVPNAccessGateway())

    response = client.get("/api/plans")

    assert response.status_code == 200


def test_plans_endpoint_lists_purchasable_plans() -> None:
    from spiritvpn_bot.application.plans import PlanCatalog
    from spiritvpn_bot.domain.entities.money import Money
    from spiritvpn_bot.domain.entities.plan import Plan

    catalog = PlanCatalog(
        {
            "nl-30d": Plan(
                id="nl-30d",
                title="Netherlands, 30 days",
                fleet_id=2,
                duration_days=30,
                quota_bytes=100 * 1024**3,
                price=Money(29900, "RUB"),
                purchasable=True,
            )
        }
    )
    uow = FakeUnitOfWork(InMemoryOrderRepository(), InMemoryCommandSequenceRepository())
    app = create_app(
        get_my_links=GetMyLinksUseCase(FakeVPNAccessGateway()),
        get_subscription_status=lambda: GetSubscriptionStatusUseCase(uow, FakeClock(NOW)),
        token_signer=SubscriptionTokenSigner(SIGNING_KEY),
        bot_token=BOT_TOKEN,
        subscription_base_url=SUBSCRIPTION_BASE_URL,
        plans=catalog,
    )
    client = TestClient(app)

    response = client.get("/api/plans")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "nl-30d",
            "title": "Netherlands, 30 days",
            "duration_days": 30,
            "quota_bytes": 100 * 1024**3,
            "display_as_unlimited": False,
            "price_amount_minor": 29900,
            "price_currency": "RUB",
        }
    ]


def test_init_data_older_than_a_second_ago_still_works() -> None:
    # sanity check that clock skew of a couple of seconds between test and
    # assertion doesn't flake this suite
    init_data = sign_init_data(valid_fields(user_id=1, auth_date=int(time.time()) - 2))
    client = make_client(FakeVPNAccessGateway())

    response = client.get("/api/me/links", headers={"X-Telegram-Init-Data": init_data})

    assert response.status_code == 200
