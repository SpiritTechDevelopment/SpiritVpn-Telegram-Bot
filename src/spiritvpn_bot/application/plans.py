from __future__ import annotations

from spiritvpn_bot.application.errors import PlanNotFound
from spiritvpn_bot.domain.entities.money import Money
from spiritvpn_bot.domain.entities.plan import Plan

FRIENDS_FREE_PLAN_ID = "friends-free"
PAID_1_MONTH_PLAN_ID = "paid-1m"
PAID_3_MONTH_PLAN_ID = "paid-3m"


class PlanCatalog:
    """Каталог планов."""

    def __init__(self, plans: dict[str, Plan]) -> None:
        self._plans = plans

    def get(self, plan_id: str) -> Plan:
        """Возвращает план по ID.

        Args:
            plan_id: ID плана.

        Returns:
            План.

        Raises:
            PlanNotFound: плана с таким id в каталоге нет.
        """
        plan = self._plans.get(plan_id)
        if plan is None:
            raise PlanNotFound(plan_id)
        return plan

    def all(self) -> list[Plan]:
        return list(self._plans.values())

    def purchasable(self) -> list[Plan]:
        """Планы для публичной витрины мини-аппа."""
        return [plan for plan in self._plans.values() if plan.purchasable]


def build_plan_catalog(
    *, friends_fleet_id: int, friends_quota_bytes: int, friends_duration_days: int
) -> PlanCatalog:
    """Собирает каталог планов из настроек процесса.

    Args:
        friends_fleet_id: vpn_fleet_id, который получают приглашённые.
        friends_quota_bytes: квота трафика на ноду для бесплатного плана.
        friends_duration_days: срок действия бесплатного плана в днях.

    Returns:
        Каталог с friends-free
    """
    return PlanCatalog(
        {
            FRIENDS_FREE_PLAN_ID: Plan(
                id=FRIENDS_FREE_PLAN_ID,
                title="Для своих: бесплатный доступ",
                fleet_id=friends_fleet_id,
                duration_days=friends_duration_days,
                quota_bytes=friends_quota_bytes,
                price=Money(0, "RUB"),
            ),
            PAID_1_MONTH_PLAN_ID: Plan(
                id=PAID_1_MONTH_PLAN_ID,
                title="1 месяц",
                fleet_id=friends_fleet_id,  # TODO: реальный fleet_id платных тарифов
                duration_days=30,
                quota_bytes=100 * 1024**3,
                price=Money(10000, "RUB"),
                purchasable=True,
                display_as_unlimited=True,
            ),
            PAID_3_MONTH_PLAN_ID: Plan(
                id=PAID_3_MONTH_PLAN_ID,
                title="3 месяца",
                fleet_id=friends_fleet_id,  # TODO: реальный fleet_id платных тарифов
                duration_days=90,
                quota_bytes=100 * 1024**3,
                price=Money(30000, "RUB"),
                purchasable=True,
                display_as_unlimited=True,
            ),
        }
    )
