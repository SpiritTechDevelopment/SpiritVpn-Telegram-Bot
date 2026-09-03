from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from spiritvpn_bot.application.builders.subscription_content_builder import (
    build_subscription_content,
)
from spiritvpn_bot.application.plans import PlanCatalog
from spiritvpn_bot.application.ports.clock import Clock
from spiritvpn_bot.application.ports.vpn_gateway import AccessLink
from spiritvpn_bot.application.subscription_token import SubscriptionTokenSigner
from spiritvpn_bot.application.use_cases.get_my_links import GetMyLinksUseCase
from spiritvpn_bot.application.use_cases.get_subscription_status import (
    GetSubscriptionStatusUseCase,
)
from spiritvpn_bot.logging import get_logger
from spiritvpn_bot.presentation.mini_app_api.auth import InitDataError, validate_init_data
from spiritvpn_bot.presentation.mini_app_api.schemas import (
    LinkStatusOut,
    PlanOut,
    SubscriptionStatusOut,
    SubscriptionUrlOut,
)

_STATIC_DIR = Path(__file__).parent / "static"
_SUBSCRIPTION_STATE_PLACEHOLDER = "__SPIRITVPN_STATE__"

_RU_MONTHS_GENITIVE = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}

logger = get_logger(__name__)


def _link_label(link: AccessLink) -> str | None:
    """Имя ссылки из фрагмента vless://...#имя, если оно есть.
    Args:
        link: объект ссылки.
    Returns:
        Имя ссылки или None, если его нет.
    """
    if not link.uri:
        return None
    fragment = urlsplit(link.uri).fragment
    return unquote(fragment) or None


def _format_ru_date(dt: datetime) -> str:
    """Дата в формате «19 сентября 2026» для браузерной страницы подписки."""
    return f"{dt.day} {_RU_MONTHS_GENITIVE[dt.month]} {dt.year}"


def _wants_html(accept: str) -> bool:
    """Браузер шлёт `Accept: text/html,...`, VLESS-клиенты — нет.

    Используется для ветвления `/s/{token}` между HTML-страницей и raw-подпиской.
    """
    return "text/html" in accept.lower()


def create_app(
    *,
    get_my_links: GetMyLinksUseCase,
    get_subscription_status: Callable[[], GetSubscriptionStatusUseCase],
    token_signer: SubscriptionTokenSigner,
    bot_token: str,
    subscription_base_url: str,
    plans: PlanCatalog,
    main_deep_link: str,
    clock: Clock,
) -> FastAPI:
    """Собирает FastAPI-приложение мини-аппа и публичного эндпоинта подписки.

    Args:
        get_my_links: use case чтения текущих ссылок клиента.
        get_subscription_status: фабрика use case'а остатка срока — своя
            SqlAlchemyUnitOfWork на вызов, как и другие DB-bound use case'ы.
        token_signer: подпись/проверка токена подписочного эндпоинта.
        bot_token: токен бота — нужен для проверки initData мини-аппа.
        subscription_base_url: публичный базовый URL для /s/{token}.
        plans: каталог планов — /api/plans отдаёт только purchasable().
        main_deep_link: ссылка t.me на бота — для браузерной страницы /s/{token}.
        clock: источник текущего времени — та же абстракция, что и в use case'ах,
            чтобы браузерная страница подписки была детерминирована в тестах.

    Returns:
        Готовое приложение FastAPI.
    """
    app = FastAPI(title="SpiritVPN Bot mini app")
    app.mount(
        "/static/clients", StaticFiles(directory=_STATIC_DIR / "clients"), name="client-icons"
    )
    subscription_html_template = (_STATIC_DIR / "subscription.html").read_text(encoding="utf-8")

    async def _render_subscription_page(*, token: str, customer_id: str) -> HTMLResponse:
        """Браузерная HTML-страница подписки — отдаётся вместо raw-подписки,
        когда `/s/{token}` открывают в браузере, а не в VLESS-клиенте.
        """
        status = await get_subscription_status().execute(customer_id=customer_id)
        if status is None:
            state_status = "none"
            expires_at_label = None
        elif status.expires_at <= clock.now():
            state_status = "expired"
            expires_at_label = None
        else:
            state_status = "active"
            expires_at_label = _format_ru_date(status.expires_at)

        links = await get_my_links.execute(customer_id=customer_id)
        servers = [
            {"name": _link_label(link), "uri": link.uri} for link in links if link.uri is not None
        ]

        state = {
            "botDeepLink": main_deep_link,
            "subscriptionUrl": f"{subscription_base_url}/s/{token}",
            "status": state_status,
            "expiresAtLabel": expires_at_label,
            "servers": servers,
        }
        state_json = json.dumps(state, ensure_ascii=False).replace("<", "\\u003c")
        html = subscription_html_template.replace(_SUBSCRIPTION_STATE_PLACEHOLDER, state_json)
        return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})

    def _authenticate(x_telegram_init_data: str) -> str:
        try:
            user_id = validate_init_data(x_telegram_init_data, bot_token=bot_token)
        except InitDataError as exc:
            logger.warning("init_data_rejected", error=str(exc))
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return f"tg:{user_id}"

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/s/{token}", response_model=None)
    async def subscription(
        token: str, accept: str = Header(default="")
    ) -> PlainTextResponse | HTMLResponse:
        customer_id = token_signer.verify(token)
        if customer_id is None:
            logger.warning("subscription_token_rejected")
            raise HTTPException(status_code=404)

        if _wants_html(accept):
            return await _render_subscription_page(token=token, customer_id=customer_id)

        links = await get_my_links.execute(customer_id=customer_id)
        body = build_subscription_content(links).decode("ascii")
        headers = {"Content-Disposition": 'attachment; filename="SpiritVPN"'}
        status = await get_subscription_status().execute(customer_id=customer_id)
        if status is not None:
            expire = int(status.expires_at.timestamp())
            headers["Subscription-Userinfo"] = f"upload=0; download=0; total=0; expire={expire}"
        return PlainTextResponse(content=body, headers=headers)

    @app.get("/api/me/links", response_model=list[LinkStatusOut])
    async def my_links(x_telegram_init_data: str = Header(...)) -> list[LinkStatusOut]:
        customer_id = _authenticate(x_telegram_init_data)
        links = await get_my_links.execute(customer_id=customer_id)
        return [
            LinkStatusOut(
                state=link.state,
                label=_link_label(link),
                block_reason=link.block_reason,
            )
            for link in links
        ]

    @app.get("/api/me/subscription-status", response_model=SubscriptionStatusOut)
    async def my_subscription_status(
        x_telegram_init_data: str = Header(...),
    ) -> SubscriptionStatusOut:
        customer_id = _authenticate(x_telegram_init_data)
        status = await get_subscription_status().execute(customer_id=customer_id)
        return SubscriptionStatusOut(days_left=status.days_left if status is not None else None)

    @app.get("/api/me/subscription-url", response_model=SubscriptionUrlOut)
    async def my_subscription_url(x_telegram_init_data: str = Header(...)) -> SubscriptionUrlOut:
        customer_id = _authenticate(x_telegram_init_data)
        token = token_signer.sign(customer_id)
        return SubscriptionUrlOut(url=f"{subscription_base_url}/s/{token}")

    @app.get("/api/plans", response_model=list[PlanOut])
    async def public_plans() -> list[PlanOut]:
        return [
            PlanOut(
                id=plan.id,
                title=plan.title,
                duration_days=plan.duration_days,
                quota_bytes=plan.quota_bytes,
                display_as_unlimited=plan.display_as_unlimited,
                price_amount_minor=plan.price.amount_minor,
                price_currency=plan.price.currency,
            )
            for plan in plans.purchasable()
        ]

    index_html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
    privacy_html = (_STATIC_DIR / "privacy.html").read_text(encoding="utf-8")
    terms_html = (_STATIC_DIR / "terms.html").read_text(encoding="utf-8")

    @app.get("/", response_class=HTMLResponse)
    async def mini_app_page() -> HTMLResponse:
        return HTMLResponse(content=index_html, headers={"Cache-Control": "no-store"})

    @app.get("/privacy", response_class=HTMLResponse)
    async def privacy_page() -> HTMLResponse:
        return HTMLResponse(content=privacy_html)

    @app.get("/terms", response_class=HTMLResponse)
    async def terms_page() -> HTMLResponse:
        return HTMLResponse(content=terms_html)

    return app
