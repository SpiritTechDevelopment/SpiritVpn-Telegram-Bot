"""Контрактные тесты SpiritVPNGateway.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import grpc
import pytest
import pytest_asyncio

from spiritvpn.customer.v1.customer_pb2 import (
    AccessBlockReason as PbBlockReason,
)
from spiritvpn.customer.v1.customer_pb2 import (
    AccessKind as PbAccessKind,
)
from spiritvpn.customer.v1.customer_pb2 import (
    AccessLinkState as PbAccessState,
)
from spiritvpn.customer.v1.customer_pb2 import (
    ApplyCustomerAccessRequest,
    ApplyCustomerAccessResponse,
    CustomerAccessLink,
    GetCustomerAccessLinksResponse,
)
from spiritvpn.customer.v1.customer_pb2_grpc import (
    CustomerAccessServiceServicer,
    CustomerAccessServiceStub,
    add_CustomerAccessServiceServicer_to_server,
)
from spiritvpn_bot.application.errors import (
    CustomerNotFound,
    ExpiryRegression,
    FleetMismatch,
    FleetNotFound,
    VPNGatewayError,
)
from spiritvpn_bot.infrastructure.spiritvpn_grpc.gateway import SpiritVPNGateway


class FakeCustomerAccessServicer(CustomerAccessServiceServicer):

    def __init__(self) -> None:
        self.received_apply: list[ApplyCustomerAccessRequest] = []
        self.apply_error: tuple[grpc.StatusCode, str] | None = None
        self.links_by_customer: dict[str, list[CustomerAccessLink]] = {}
        self.links_error: tuple[grpc.StatusCode, str] | None = None

    async def ApplyCustomerAccess(self, request, context):  # noqa: N802
        if self.apply_error is not None:
            code, message = self.apply_error
            await context.abort(code, message)
        self.received_apply.append(request)
        return ApplyCustomerAccessResponse()

    async def GetCustomerAccessLinks(self, request, context):  # noqa: N802
        if self.links_error is not None:
            code, message = self.links_error
            await context.abort(code, message)
        return GetCustomerAccessLinksResponse(
            links=self.links_by_customer.get(request.customer_id, [])
        )


@pytest_asyncio.fixture
async def fixture() -> AsyncIterator[tuple[FakeCustomerAccessServicer, SpiritVPNGateway]]:
    servicer = FakeCustomerAccessServicer()
    server = grpc.aio.server()
    add_CustomerAccessServiceServicer_to_server(servicer, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()

    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    gateway = SpiritVPNGateway(CustomerAccessServiceStub(channel))

    try:
        yield servicer, gateway
    finally:
        await channel.close()
        await server.stop(None)


EXPIRES_AT = datetime(2026, 2, 1, tzinfo=UTC)


async def test_apply_access_sends_correct_request(
    fixture: tuple[FakeCustomerAccessServicer, SpiritVPNGateway],
) -> None:
    servicer, gateway = fixture

    await gateway.apply_access(
        customer_id="tg:1",
        fleet_id=1,
        quota_bytes=100 * 1024**3,
        expires_at=EXPIRES_AT,
        command_number=1,
    )

    assert len(servicer.received_apply) == 1
    request = servicer.received_apply[0]
    assert request.customer_id == "tg:1"
    assert request.vpn_fleet_id == 1
    assert request.usage_quota_bytes == 100 * 1024**3
    assert request.expires_at_epoch_sec == int(EXPIRES_AT.timestamp())
    assert request.command_number == 1


async def test_apply_access_not_found_maps_to_fleet_not_found(
    fixture: tuple[FakeCustomerAccessServicer, SpiritVPNGateway],
) -> None:
    servicer, gateway = fixture
    servicer.apply_error = (grpc.StatusCode.NOT_FOUND, "fleet не найден")

    with pytest.raises(FleetNotFound):
        await gateway.apply_access(
            customer_id="tg:1",
            fleet_id=999,
            quota_bytes=1,
            expires_at=EXPIRES_AT,
            command_number=1,
        )


async def test_apply_access_fleet_mismatch(
    fixture: tuple[FakeCustomerAccessServicer, SpiritVPNGateway],
) -> None:
    servicer, gateway = fixture
    servicer.apply_error = (
        grpc.StatusCode.FAILED_PRECONDITION,
        "customer уже привязан к другому fleet",
    )

    with pytest.raises(FleetMismatch):
        await gateway.apply_access(
            customer_id="tg:1", fleet_id=2, quota_bytes=1, expires_at=EXPIRES_AT, command_number=2
        )


async def test_apply_access_expiry_regression(
    fixture: tuple[FakeCustomerAccessServicer, SpiritVPNGateway],
) -> None:
    servicer, gateway = fixture
    servicer.apply_error = (
        grpc.StatusCode.FAILED_PRECONDITION,
        "сокращение expires_at не поддерживается",
    )

    with pytest.raises(ExpiryRegression):
        await gateway.apply_access(
            customer_id="tg:1", fleet_id=1, quota_bytes=1, expires_at=EXPIRES_AT, command_number=2
        )


async def test_apply_access_unmapped_error_stays_generic_with_stable_code(
    fixture: tuple[FakeCustomerAccessServicer, SpiritVPNGateway],
) -> None:
    servicer, gateway = fixture
    servicer.apply_error = (grpc.StatusCode.INTERNAL, "внутренняя ошибка")

    with pytest.raises(VPNGatewayError) as exc_info:
        await gateway.apply_access(
            customer_id="tg:1", fleet_id=1, quota_bytes=1, expires_at=EXPIRES_AT, command_number=2
        )
    assert exc_info.value.stable_code == "INTERNAL"


async def test_get_links_returns_ready_link_with_uri(
    fixture: tuple[FakeCustomerAccessServicer, SpiritVPNGateway],
) -> None:
    servicer, gateway = fixture
    servicer.links_by_customer["tg:1"] = [
        CustomerAccessLink(
            kind=PbAccessKind.ACCESS_KIND_FREEDOM,
            state=PbAccessState.ACCESS_LINK_STATE_READY,
            uri="vless://uuid@nl.example.com:443?...#Netherlands",
        )
    ]

    links = await gateway.get_links(customer_id="tg:1")

    assert len(links) == 1
    assert links[0].kind == "FREEDOM"
    assert links[0].state == "READY"
    assert links[0].uri == "vless://uuid@nl.example.com:443?...#Netherlands"
    assert links[0].block_reason is None


async def test_get_links_returns_blocked_link_with_reason(
    fixture: tuple[FakeCustomerAccessServicer, SpiritVPNGateway],
) -> None:
    servicer, gateway = fixture
    servicer.links_by_customer["tg:1"] = [
        CustomerAccessLink(
            kind=PbAccessKind.ACCESS_KIND_BRIDGE,
            state=PbAccessState.ACCESS_LINK_STATE_BLOCKED,
            block_reason=PbBlockReason.ACCESS_BLOCK_REASON_TRAFFIC_QUOTA_EXHAUSTED,
        )
    ]

    links = await gateway.get_links(customer_id="tg:1")

    assert links[0].kind == "BRIDGE"
    assert links[0].state == "BLOCKED"
    assert links[0].block_reason == "TRAFFIC_QUOTA_EXHAUSTED"
    assert links[0].uri is None


async def test_get_links_unknown_customer_maps_to_customer_not_found(
    fixture: tuple[FakeCustomerAccessServicer, SpiritVPNGateway],
) -> None:
    servicer, gateway = fixture
    servicer.links_error = (grpc.StatusCode.NOT_FOUND, "customer не найден")

    with pytest.raises(CustomerNotFound):
        await gateway.get_links(customer_id="tg:missing")
