from __future__ import annotations

from spiritvpn_bot.application.errors import CustomerNotFound
from spiritvpn_bot.application.ports.vpn_gateway import AccessLink
from spiritvpn_bot.application.use_cases.get_my_links import GetMyLinksUseCase
from tests.unit.application.fakes import FakeVPNAccessGateway


async def test_returns_all_bridge_links() -> None:
    gateway = FakeVPNAccessGateway()
    gateway.links_by_customer["tg:1"] = [
        AccessLink(kind="BRIDGE", state="READY", uri="vless://bridge#NL Amsterdam"),
        AccessLink(kind="BRIDGE", state="PENDING"),
    ]
    use_case = GetMyLinksUseCase(gateway)

    links = await use_case.execute(customer_id="tg:1")

    assert links == gateway.links_by_customer["tg:1"]


async def test_includes_freedom_links_labelled_as_russian() -> None:
    gateway = FakeVPNAccessGateway()
    legacy_name = AccessLink(kind="FREEDOM", state="READY", uri="vless://freedom#russia")
    new_convention = AccessLink(kind="FREEDOM", state="READY", uri="vless://freedom#RU Moscow 1")
    gateway.links_by_customer["tg:1"] = [legacy_name, new_convention]
    use_case = GetMyLinksUseCase(gateway)

    links = await use_case.execute(customer_id="tg:1")

    assert links == [legacy_name, new_convention]


async def test_excludes_freedom_links_not_labelled_as_russian() -> None:
    gateway = FakeVPNAccessGateway()
    gateway.links_by_customer["tg:1"] = [
        AccessLink(kind="FREEDOM", state="READY", uri="vless://freedom#NL Amsterdam"),
        AccessLink(kind="FREEDOM", state="READY", uri="vless://freedom"),  # без имени
        AccessLink(kind="FREEDOM", state="PENDING"),  # без uri вообще
    ]
    use_case = GetMyLinksUseCase(gateway)

    links = await use_case.execute(customer_id="tg:1")

    assert links == []


async def test_unknown_customer_returns_empty_list_instead_of_raising() -> None:
    gateway = FakeVPNAccessGateway()
    gateway.raise_on_get_links = CustomerNotFound("CUSTOMER_NOT_FOUND", "customer не найден")
    use_case = GetMyLinksUseCase(gateway)

    links = await use_case.execute(customer_id="tg:missing")

    assert links == []
