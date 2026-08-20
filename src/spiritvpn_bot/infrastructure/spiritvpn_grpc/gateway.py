from __future__ import annotations

from datetime import datetime

import grpc

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
    CustomerAccessLink,
    GetCustomerAccessLinksRequest,
)
from spiritvpn.customer.v1.customer_pb2_grpc import CustomerAccessServiceStub
from spiritvpn_bot.application.errors import (
    CustomerNotFound,
    ExpiryRegression,
    FleetMismatch,
    FleetNotFound,
    VPNGatewayError,
)
from spiritvpn_bot.application.ports.vpn_gateway import (
    AccessKind,
    AccessLink,
    AccessState,
    BlockReason,
)
from spiritvpn_bot.logging import get_logger

_KIND_FROM_PB: dict[int, AccessKind] = {
    PbAccessKind.ACCESS_KIND_FREEDOM: "FREEDOM",
    PbAccessKind.ACCESS_KIND_BRIDGE: "BRIDGE",
}

_STATE_FROM_PB: dict[int, AccessState] = {
    PbAccessState.ACCESS_LINK_STATE_PENDING: "PENDING",
    PbAccessState.ACCESS_LINK_STATE_READY: "READY",
    PbAccessState.ACCESS_LINK_STATE_BLOCKED: "BLOCKED",
    PbAccessState.ACCESS_LINK_STATE_FAILED: "FAILED",
}

_BLOCK_REASON_FROM_PB: dict[int, BlockReason] = {
    PbBlockReason.ACCESS_BLOCK_REASON_TIME_EXPIRED: "TIME_EXPIRED",
    PbBlockReason.ACCESS_BLOCK_REASON_TRAFFIC_QUOTA_EXHAUSTED: "TRAFFIC_QUOTA_EXHAUSTED",
}

_FAILED_PRECONDITION_APPLY_ERRORS: dict[str, type[VPNGatewayError]] = {
    "customer уже привязан к другому fleet": FleetMismatch,
    "сокращение expires_at не поддерживается": ExpiryRegression,
}

logger = get_logger(__name__)


class SpiritVPNGateway:
    """Реализация VPNAccessGateway поверх сгенерированного gRPC-стаба.

    Единственное место в кодовой базе, где существуют protobuf-типы и коды
    grpc.StatusCode — дальше наружу уходят только AccessLink и подклассы
    VPNGatewayError.
    """

    def __init__(self, stub: CustomerAccessServiceStub) -> None:
        self._stub = stub

    async def apply_access(
        self,
        *,
        customer_id: str,
        fleet_id: int,
        quota_bytes: int,
        expires_at: datetime,
        command_number: int,
    ) -> None:
        request = ApplyCustomerAccessRequest(
            customer_id=customer_id,
            vpn_fleet_id=fleet_id,
            usage_quota_bytes=quota_bytes,
            expires_at_epoch_sec=int(expires_at.timestamp()),
            command_number=command_number,
        )
        log = logger.bind(customer_id=customer_id, fleet_id=fleet_id, command_number=command_number)
        log.info("apply_customer_access_call")
        try:
            await self._stub.ApplyCustomerAccess(request)
        except grpc.aio.AioRpcError as exc:
            log.warning(
                "apply_customer_access_failed", grpc_code=exc.code().name, details=exc.details()
            )
            raise _translate_apply_error(exc) from exc
        log.info("apply_customer_access_ok")

    async def get_links(self, *, customer_id: str) -> list[AccessLink]:
        request = GetCustomerAccessLinksRequest(customer_id=customer_id)
        log = logger.bind(customer_id=customer_id)
        try:
            response = await self._stub.GetCustomerAccessLinks(request)
        except grpc.aio.AioRpcError as exc:
            log.warning(
                "get_customer_access_links_failed",
                grpc_code=exc.code().name,
                details=exc.details(),
            )
            raise _translate_get_links_error(exc) from exc
        links = [_to_access_link(link) for link in response.links]
        log.info("get_customer_access_links_ok", link_count=len(links))
        return links


def _to_access_link(link: CustomerAccessLink) -> AccessLink:
    kind = _KIND_FROM_PB.get(link.kind)
    state = _STATE_FROM_PB.get(link.state)
    if kind is None or state is None:
        raise VPNGatewayError(
            "UNKNOWN_ENUM_VALUE", f"неизвестный kind={link.kind} или state={link.state}"
        )
    block_reason = (
        _BLOCK_REASON_FROM_PB.get(link.block_reason) if link.HasField("block_reason") else None
    )
    uri = link.uri if link.HasField("uri") else None
    return AccessLink(kind=kind, state=state, uri=uri, block_reason=block_reason)


def _translate_apply_error(exc: grpc.aio.AioRpcError) -> Exception:
    code = exc.code()
    message = exc.details() or ""

    if code == grpc.StatusCode.NOT_FOUND:
        return FleetNotFound("FLEET_NOT_FOUND", message)
    if code == grpc.StatusCode.FAILED_PRECONDITION:
        specific = _FAILED_PRECONDITION_APPLY_ERRORS.get(message)
        if specific is not None:
            return specific(code.name, message)
        return VPNGatewayError(code.name, message)

    return VPNGatewayError(code.name, message)


def _translate_get_links_error(exc: grpc.aio.AioRpcError) -> Exception:
    code = exc.code()
    message = exc.details() or ""

    if code == grpc.StatusCode.NOT_FOUND:
        return CustomerNotFound("CUSTOMER_NOT_FOUND", message)

    return VPNGatewayError(code.name, message)
