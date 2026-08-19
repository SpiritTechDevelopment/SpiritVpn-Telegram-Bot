from __future__ import annotations


class OrderNotFound(Exception):
    """Ошибка, обозначающиая, что заказ с таким order_id не найден в репозитории.

    Args:
        order_id: ID заказа, который не удалось найти.
    """

    def __init__(self, order_id: str) -> None:
        super().__init__(f"order {order_id} not found")
        self.order_id = order_id


class PlanNotFound(Exception):
    """plan_id не найден в каталоге планов — внутренний сбой конфигурации.

    Args:
        plan_id: ID плана, которого нет в каталоге.
    """

    def __init__(self, plan_id: str) -> None:
        super().__init__(f"plan {plan_id} not found in catalog")
        self.plan_id = plan_id


class VPNGatewayError(Exception):
    """Base класс ошибок, переведённых из кодов spiritvpnd.

    Args:
        stable_code: код ошибки из ответа spiritvpnd.
        message: текст ошибки, OUT
    """

    def __init__(self, stable_code: str, message: str) -> None:
        super().__init__(f"{stable_code}: {message}")
        self.stable_code = stable_code


class CustomerNotFound(VPNGatewayError):
    """GetCustomerAccessLinks для customer_id, которого spiritvpnd не видел."""


class FleetNotFound(VPNGatewayError):
    """Продажа плана, чей fleet_id больше не присутствует в манифесте."""


class FleetMismatch(VPNGatewayError):
    """Попытка перевести существующего клиента на другой fleet_id."""


class ExpiryRegression(VPNGatewayError):
    """Отправлен expires_at раньше уже сохранённого для этого клиента."""
