from __future__ import annotations

from pydantic import BaseModel

from spiritvpn_bot.application.ports.vpn_gateway import AccessKind, AccessState, BlockReason


class LinkStatusOut(BaseModel):
    """Статус одного доступа для мини-аппа.

    Осознанно без uri: сама ссылка отдаётся только через подписочный
    эндпоинт (/s/{token}), не через JSON, который проще случайно залогировать
    или закешировать где не следует.
    """

    kind: AccessKind
    state: AccessState
    block_reason: BlockReason | None = None


class SubscriptionUrlOut(BaseModel):
    url: str


class PlanOut(BaseModel):
    """Один план в публичной витрине мини-аппа."""

    id: str
    title: str
    duration_days: int
    quota_bytes: int
    price_amount_minor: int
    price_currency: str
