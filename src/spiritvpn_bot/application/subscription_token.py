from __future__ import annotations

import base64
import hashlib
import hmac


class SubscriptionTokenSigner:
    """Подписывает customer_id в самодостаточный токен для GET /s/{token}."""

    def __init__(self, signing_key: bytes) -> None:
        self._signing_key = signing_key

    def sign(self, customer_id: str) -> str:
        payload = base64.urlsafe_b64encode(customer_id.encode("utf-8")).rstrip(b"=")
        signature = self._signature(payload)
        return f"{payload.decode('ascii')}.{signature}"

    def verify(self, token: str) -> str | None:
        """Проверяет токен и достаёт из него customer_id.

        Args:
            token: значение, полученное от sign().

        Returns:
            customer_id, если подпись верна, иначе None. Не бросает
            исключение намеренно: невалидный токен в публичном URL — это
            штатный случай (опечатка, чужой перебор), а не сбой.
        """
        try:
            payload_b64, signature = token.split(".", 1)
        except ValueError:
            return None
        if not hmac.compare_digest(signature, self._signature(payload_b64.encode("ascii"))):
            return None
        padding = "=" * (-len(payload_b64) % 4)
        try:
            return base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return None

    def _signature(self, payload: bytes) -> str:
        digest = hmac.new(self._signing_key, payload, hashlib.sha256).hexdigest()
        return digest[:32]
