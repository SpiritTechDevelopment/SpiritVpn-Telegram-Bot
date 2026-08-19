from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class InitDataError(Exception):
    """initData не прошла проверку подлинности."""


def validate_init_data(init_data: str, *, bot_token: str, max_age_seconds: int = 3600) -> int:
    """Проверяет подпись Telegram WebApp initData и возвращает telegram user id.

    Args:
        init_data: сырая строка Telegram.WebApp.initData.
        bot_token: токен бота, тот же, что и у BotFather.
        max_age_seconds: сколько секунд считать auth_date свежим.

    Returns:
        telegram user id из проверенных данных.

    Raises:
        InitDataError: подпись не совпала, данные протухли или не распарсились.
    """
    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError as exc:
        raise InitDataError("initData не парсится как query string") from exc

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("initData без hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise InitDataError("подпись initData не совпадает")

    auth_date = pairs.get("auth_date")
    if auth_date is None:
        raise InitDataError("initData без auth_date")
    try:
        age = time.time() - int(auth_date)
    except ValueError as exc:
        raise InitDataError("auth_date не число") from exc
    if age > max_age_seconds:
        raise InitDataError("initData устарела")

    user_raw = pairs.get("user")
    if not user_raw:
        raise InitDataError("initData без поля user")
    try:
        user = json.loads(user_raw)
        return int(user["id"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise InitDataError("не удалось разобрать поле user") from exc
