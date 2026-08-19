from __future__ import annotations

import base64

from spiritvpn_bot.application.ports.vpn_gateway import AccessLink


def build_subscription_content(links: list[AccessLink]) -> bytes:
    """Собирает тело подписочной ссылки: base64 от готовых vless:// через \\n.

    Args:
        links: ссылки клиента, как их вернул VPNAccessGateway.get_links.

    Returns:
        Тело HTTP-ответа подписки, уже закодированное в base64. Ссылки не в
        состоянии READY (ещё разворачиваются, заблокированы по сроку или
        квоте) в тело не попадают
    """
    uris = [link.uri for link in links if link.state == "READY" and link.uri]
    body = "\n".join(uris)
    return base64.b64encode(body.encode("utf-8"))
