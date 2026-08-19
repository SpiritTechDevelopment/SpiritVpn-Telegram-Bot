from __future__ import annotations

import uuid


class UuidIdGenerator:
    def new_order_id(self) -> str:
        return str(uuid.uuid4())
