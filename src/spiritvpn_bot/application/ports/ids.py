from __future__ import annotations

from typing import Protocol


class IdGenerator(Protocol):
    def new_order_id(self) -> str: ...
