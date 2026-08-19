from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from spiritvpn_bot.application.builders.subscription_content_builder import (
    build_subscription_content,
)
from spiritvpn_bot.application.plans import PlanCatalog
from spiritvpn_bot.application.subscription_token import SubscriptionTokenSigner
from spiritvpn_bot.application.use_cases.get_my_links import GetMyLinksUseCase
from spiritvpn_bot.presentation.mini_app_api.auth import InitDataError, validate_init_data
from spiritvpn_bot.presentation.mini_app_api.schemas import (
    LinkStatusOut,
    PlanOut,
    SubscriptionUrlOut,
)

_STATIC_DIR = Path(__file__).parent / "static"


def create_app(
    *,
    get_my_links: GetMyLinksUseCase,
    token_signer: SubscriptionTokenSigner,
    bot_token: str,
    subscription_base_url: str,
    plans: PlanCatalog,
) -> FastAPI:
    """Собирает FastAPI-приложение мини-аппа и публичного эндпоинта подписки.

    Args:
        get_my_links: use case чтения текущих ссылок клиента.
        token_signer: подпись/проверка токена подписочного эндпоинта.
        bot_token: токен бота — нужен для проверки initData мини-аппа.
        subscription_base_url: публичный базовый URL для /s/{token}.
        plans: каталог планов — /api/plans отдаёт только purchasable().

    Returns:
        Готовое приложение FastAPI.
    """
    app = FastAPI(title="SpiritVPN Bot mini app")

    def _authenticate(x_telegram_init_data: str) -> str:
        try:
            user_id = validate_init_data(x_telegram_init_data, bot_token=bot_token)
        except InitDataError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return f"tg:{user_id}"

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/s/{token}", response_class=PlainTextResponse)
    async def subscription(token: str) -> str:
        customer_id = token_signer.verify(token)
        if customer_id is None:
            raise HTTPException(status_code=404)
        links = await get_my_links.execute(customer_id=customer_id)
        return build_subscription_content(links).decode("ascii")

    @app.get("/api/me/links", response_model=list[LinkStatusOut])
    async def my_links(x_telegram_init_data: str = Header(...)) -> list[LinkStatusOut]:
        customer_id = _authenticate(x_telegram_init_data)
        links = await get_my_links.execute(customer_id=customer_id)
        return [
            LinkStatusOut(kind=link.kind, state=link.state, block_reason=link.block_reason)
            for link in links
        ]

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
                price_amount_minor=plan.price.amount_minor,
                price_currency=plan.price.currency,
            )
            for plan in plans.purchasable()
        ]

    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")

    return app
