from __future__ import annotations

from spiritvpn_bot.domain.errors import StaleCommandNumber


def next_command_number(last_issued: int | None) -> int:
    """Возвращает command_number для следующего вызова ApplyCustomerAccess.

    Args:
        last_issued: последний выданный номер для клиента, либо None, если
            для него ещё не выдавалось ни одной команды.

    Returns:
        Следующий номер команды.
    """
    return (last_issued or 0) + 1


def ensure_monotonic(candidate: int, last_issued: int | None) -> None:
    """Проверяет, что candidate строго больше last_issued.

    Args:
        candidate: номер, который планируется отправить.
        last_issued: последний выданный номер, либо None.

    Raises:
        StaleCommandNumber: если candidate не больше last_issued.
    """
    if last_issued is not None and candidate <= last_issued:
        raise StaleCommandNumber(candidate, last_issued)
