from __future__ import annotations


class OrderNotFound(Exception):
    """Заказ с таким order_id не найден в репозитории.

    Args:
        order_id: идентификатор заказа, который не удалось найти.
    """

    def __init__(self, order_id: str) -> None:
        super().__init__(f"order {order_id} not found")
        self.order_id = order_id


class VPNGatewayError(Exception):
    """Base класс ошибок, переведённых из кодов spiritvpnd.

    Args:
        stable_code: стабильный код ошибки из ответа spiritvpnd.
        message: текст ошибки, ушедший наружу.
    """

    def __init__(self, stable_code: str, message: str) -> None:
        super().__init__(f"{stable_code}: {message}")
        self.stable_code = stable_code


class CustomerNotFound(VPNGatewayError):
    """GetCustomerAccessLinks для customer_id, которого spiritvpnd не видел."""


class FleetNotFound(VPNGatewayError):
    """Продажа плана, чей fleet_id больше не присутствует в манифесте."""


class FleetMismatch(VPNGatewayError):
    """Попытка перевести существующего клиента на другой fleet_id.
    """


class ExpiryRegression(VPNGatewayError):
    """Отправлен expires_at раньше уже сохранённого для этого клиента.
    """
