from __future__ import annotations

import pytest

from spiritvpn_bot.application.errors import PlanNotFound
from spiritvpn_bot.application.plans import build_plan_catalog


def test_friends_plan_is_free() -> None:
    catalog = build_plan_catalog(
        friends_fleet_id=1, friends_quota_bytes=10, friends_duration_days=7
    )

    plan = catalog.get("friends-free")

    assert plan.price.amount_minor == 0
    assert plan.fleet_id == 1
    assert plan.quota_bytes == 10
    assert plan.duration_days == 7


def test_unknown_plan_raises() -> None:
    catalog = build_plan_catalog(
        friends_fleet_id=1, friends_quota_bytes=10, friends_duration_days=7
    )

    with pytest.raises(PlanNotFound):
        catalog.get("does-not-exist")


def test_friends_plan_is_not_in_the_public_storefront() -> None:
    # friends-free — для своих, не для витрины мини-аппа
    catalog = build_plan_catalog(
        friends_fleet_id=1, friends_quota_bytes=10, friends_duration_days=7
    )

    assert catalog.purchasable() == []
