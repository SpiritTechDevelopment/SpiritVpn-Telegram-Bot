from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from spiritvpn_bot.application.ports.vpn_gateway import AccessLink, VPNAccessGateway


class CreateDevAccessLinkUseCase:
    """Dev/тест-утилита: выдаёт доступ рандомному customer_id на N минут и
    M байт, минуя Order/оплату."""

    def __init__(
        self,
        gateway: VPNAccessGateway,
        fleet_id: int,
        *,
        max_attempts: int = 15,
        poll_interval_seconds: float = 2.0,
    ) -> None:
        self._gateway = gateway
        self._fleet_id = fleet_id
        self._max_attempts = max_attempts
        self._poll_interval_seconds = poll_interval_seconds

    async def execute(self, *, minutes: int, num_bytes: int) -> tuple[str, list[AccessLink] | None]:
        """Выдаёт доступ рандомному customer_id и дожидается готовой ссылки.

        Args:
            minutes: срок действия доступа в минутах.
            num_bytes: квота трафика в байтах.

        Returns:
            (customer_id, готовые READY-ссылки с uri) либо (customer_id, None),
            если ни одна ссылка не перешла в READY за отведённое время.
        """
        customer_id = f"dev:{uuid.uuid4().hex[:12]}"
        expires_at = datetime.now(UTC) + timedelta(minutes=minutes)

        await self._gateway.apply_access(
            customer_id=customer_id,
            fleet_id=self._fleet_id,
            quota_bytes=num_bytes,
            expires_at=expires_at,
            command_number=1,
        )

        for attempt in range(self._max_attempts):
            links = await self._gateway.get_links(customer_id=customer_id)
            ready = [link for link in links if link.state == "READY" and link.uri]
            if ready:
                return customer_id, ready
            if attempt < self._max_attempts - 1:
                await asyncio.sleep(self._poll_interval_seconds)

        return customer_id, None
