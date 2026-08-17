from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class OrderPaid:
    order_id: str
    customer_id: str
    plan_id: str
    command_number: int
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AccessRequested:
    order_id: str
    customer_id: str
    command_number: int


@dataclass(frozen=True, slots=True)
class AccessBecameReady:
    order_id: str
    customer_id: str


@dataclass(frozen=True, slots=True)
class SubscriptionExpiringSoon:
    order_id: str
    customer_id: str
    expires_at: datetime
