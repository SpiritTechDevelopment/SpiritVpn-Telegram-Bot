from __future__ import annotations

from urllib.parse import unquote, urlsplit

from spiritvpn_bot.application.errors import CustomerNotFound
from spiritvpn_bot.application.ports.vpn_gateway import AccessLink, VPNAccessGateway

_LEGACY_RUSSIAN_NAMES = {"russia"}


def _is_russian_freedom_link(link: AccessLink) -> bool:
    """Определяет российскую FREEDOM-ноду по имени в фрагменте uri.

    Args:
        link: ссылка вида FREEDOM.

    Returns:
        True, если по имени в uri это российская нода.
    """
    if not link.uri:
        return False
    fragment = unquote(urlsplit(link.uri).fragment).strip()
    if not fragment:
        return False
    first_word = fragment.split(" ", 1)[0]
    if first_word.upper() == "RU":
        return True
    return fragment.lower() in _LEGACY_RUSSIAN_NAMES


class GetMyLinksUseCase:
    """Читает текущие ссылки доступа клиента у spiritvpnd."""

    def __init__(self, gateway: VPNAccessGateway) -> None:
        self._gateway = gateway

    async def execute(self, *, customer_id: str) -> list[AccessLink]:
        """Возвращает ссылки клиента.

        Args:
            customer_id: ID клиента.

        Returns:
            Ссылки вида BRIDGE (все) плюс FREEDOM, но только российские —
            остальные FREEDOM продукту не показываем (см. docs/FAQ.md).
        """
        try:
            links = await self._gateway.get_links(customer_id=customer_id)
        except CustomerNotFound:
            return []
        return [
            link
            for link in links
            if link.kind == "BRIDGE" or (link.kind == "FREEDOM" and _is_russian_freedom_link(link))
        ]
