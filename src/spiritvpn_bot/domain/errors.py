from __future__ import annotations


class DomainError(Exception):
    """Base класс ошибок бизнес правил домена."""


class NegativeMoney(DomainError):
    """Сумма транзакции не может быть отрицательной.

    Args:
        amount_minor: отрицательная сумма, вызвавшая ошибку.
    """

    def __init__(self, amount_minor: int) -> None:
        super().__init__(f"money amount cannot be negative, got {amount_minor}")
        self.amount_minor = amount_minor


class CurrencyMismatch(DomainError):
    """Операция над Money с разными валютами.

    Args:
        left: валюта первого операнда.
        right: валюта второго операнда.
    """

    def __init__(self, left: str, right: str) -> None:
        super().__init__(f"currency mismatch: {left} vs {right}")
        self.left = left
        self.right = right


class InvalidOrderTransition(DomainError):
    """Запрошен переход Order в статус, недопустимый из текущего.

    Args:
        current: статус, из которого пытались перейти.
        target: статус, в который пытались перейти.
    """

    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"order cannot move from {current} to {target}")
        self.current = current
        self.target = target


class StaleCommandNumber(DomainError):
    """command_number не больше последнего выданного для этого клиента.

    Args:
        candidate: номер, который пытались выдать.
        last: последний уже выданный номер.
    """

    def __init__(self, candidate: int, last: int) -> None:
        super().__init__(f"command_number {candidate} is not greater than last issued {last}")
        self.candidate = candidate
        self.last = last
