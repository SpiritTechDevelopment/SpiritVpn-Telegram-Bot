from __future__ import annotations

from pydantic import BaseModel

from spiritvpn_bot.application.ports.vpn_gateway import AccessKind, AccessState, BlockReason


class LinkStatusOut(BaseModel):
    """Статус одного доступа для мини-аппа."""

    kind: AccessKind
    state: AccessState
    label: str | None = None
    block_reason: BlockReason | None = None
    debug_sni: str | None = None  # DEBUG: убрать вместе с main.py::_link_debug_sni


class SubscriptionUrlOut(BaseModel):
    url: str


class PlanOut(BaseModel):
    """Один план в публичной витрине мини-аппа."""

    id: str
    title: str
    duration_days: int
    quota_bytes: int
    display_as_unlimited: bool
    price_amount_minor: int
    price_currency: str
