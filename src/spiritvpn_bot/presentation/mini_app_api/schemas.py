from __future__ import annotations

from pydantic import BaseModel

from spiritvpn_bot.application.ports.vpn_gateway import AccessState, BlockReason


class LinkStatusOut(BaseModel):
    """Статус одного доступа для мини-аппа."""

    state: AccessState
    label: str | None = None
    block_reason: BlockReason | None = None


class SubscriptionUrlOut(BaseModel):
    url: str


class SubscriptionStatusOut(BaseModel):
    """days_left — None, если у клиента ещё не было ни одной выдачи."""

    days_left: int | None


class PlanOut(BaseModel):
    """Один план в публичной витрине мини-аппа."""

    id: str
    title: str
    duration_days: int
    quota_bytes: int
    display_as_unlimited: bool
    price_amount_minor: int
    price_currency: str
