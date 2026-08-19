from __future__ import annotations

import uuid

from spiritvpn_bot.infrastructure.ids import UuidIdGenerator


def test_new_order_id_returns_unique_uuids() -> None:
    generator = UuidIdGenerator()

    first = generator.new_order_id()
    second = generator.new_order_id()

    assert uuid.UUID(first) != uuid.UUID(second)
