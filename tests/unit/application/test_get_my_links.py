from __future__ import annotations

from spiritvpn_bot.application.errors import CustomerNotFound
from spiritvpn_bot.application.ports.vpn_gateway import AccessLink
from spiritvpn_bot.application.use_cases.get_my_links import GetMyLinksUseCase
from tests.unit.application.fakes import FakeVPNAccessGateway


async def test_returns_only_bridge_links() -> None:
    gateway = FakeVPNAccessGateway()
    gateway.links_by_customer["tg:1"] = [
        AccessLink(kind="FREEDOM", state="READY", uri="vless://freedom"),
        AccessLink(kind="BRIDGE", state="READY", uri="vless://bridge"),
    ]
    use_case = GetMyLinksUseCase(gateway)

    links = await use_case.execute(customer_id="tg:1")

    assert links == [
        AccessLink(kind="BRIDGE", state="READY", uri="vless://bridge"),
    ]


async def test_unknown_customer_returns_empty_list_instead_of_raising() -> None:
    gateway = FakeVPNAccessGateway()
    gateway.raise_on_get_links = CustomerNotFound("CUSTOMER_NOT_FOUND", "customer не найден")
    use_case = GetMyLinksUseCase(gateway)

    links = await use_case.execute(customer_id="tg:missing")

    assert links == []
