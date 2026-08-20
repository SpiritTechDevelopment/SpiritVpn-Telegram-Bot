from __future__ import annotations

from spiritvpn_bot.application.errors import CustomerNotFound
from spiritvpn_bot.application.ports.vpn_gateway import AccessLink, VPNAccessGateway


class GetMyLinksUseCase:
    """Читает текущие ссылки доступа клиента у spiritvpnd."""

    def __init__(self, gateway: VPNAccessGateway) -> None:
        self._gateway = gateway

    async def execute(self, *, customer_id: str) -> list[AccessLink]:
        """Возвращает ссылки клиента.

        Args:
            customer_id: ID клиента.

        Returns:
            Все текущие ссылки клиента, любого kind.
        """
        try:
            return await self._gateway.get_links(customer_id=customer_id)
        except CustomerNotFound:
            return []
