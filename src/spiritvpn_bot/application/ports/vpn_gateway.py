from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

AccessKind = Literal["FREEDOM", "BRIDGE"]
AccessState = Literal["READY", "PENDING", "BLOCKED", "FAILED"]
BlockReason = Literal["TIME_EXPIRED", "TRAFFIC_QUOTA_EXHAUSTED"]


@dataclass(frozen=True, slots=True)
class AccessLink:
    """Одна строка ответа GetCustomerAccessLinks в spiritvpnd.

    Attributes:
        kind: вид доступа, FREEDOM или BRIDGE.
        state: текущее состояние ссылки.
        uri: готовая vless:// ссылка, если состояние READY.
        block_reason: причина блокировки, если состояние BLOCKED.
    """

    kind: AccessKind
    state: AccessState
    uri: str | None = None
    block_reason: BlockReason | None = None


class VPNAccessGateway(Protocol):
    """Entry Point для обращения к spiritvpnd.
    """

    async def apply_access(
        self,
        *,
        customer_id: str,
        fleet_id: int,
        quota_bytes: int,
        expires_at: datetime,
        command_number: int,
    ) -> None:
        """Вызывает ApplyCustomerAccess.
        Args:
            customer_id: непрозрачный идентификатор клиента.
            fleet_id: vpn_fleet_id купленного плана.
            quota_bytes: квота трафика в байтах на ноду.
            expires_at: момент истечения доступа.
            command_number: монотонно возрастающий номер команды для клиента.
        """
        ...

    async def get_links(self, *, customer_id: str) -> list[AccessLink]:
        """Вызывает GetCustomerAccessLinks.

        Args:
            customer_id: непрозрачный идентификатор клиента.

        Returns:
            Список текущих ссылок доступа клиента.

        Raises:
            CustomerNotFound: если spiritvpnd никогда не видел этот customer_id
                (то есть по клиенту ещё не проходило ни одной оплаты).
        """
        ...
