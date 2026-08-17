from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Возвращает current время, в UTC и с таймзоной.

        Returns:
            Текущий временная метка.
        """
        ...
