from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from spiritvpn_bot.presentation.mini_app_api.auth import InitDataError, validate_init_data

BOT_TOKEN = "123456:AAtest-bot-token"


def sign_init_data(fields: dict[str, str], *, bot_token: str = BOT_TOKEN) -> str:
    """Собирает валидную initData так же, как это делает клиент Telegram —
    единственный способ протестировать проверку подписи, не имея реального
    Telegram-клиента под рукой."""
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    digest = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": digest})


def valid_fields(user_id: int = 42, auth_date: int | None = None) -> dict[str, str]:
    return {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "user": json.dumps({"id": user_id, "first_name": "Friend"}),
        "query_id": "AAF1",
    }


def test_valid_init_data_returns_user_id() -> None:
    init_data = sign_init_data(valid_fields(user_id=42))

    user_id = validate_init_data(init_data, bot_token=BOT_TOKEN)

    assert user_id == 42


def test_tampered_field_is_rejected() -> None:
    fields = valid_fields(user_id=42)
    init_data = sign_init_data(fields)
    # подменяем user на другого уже после подписи — ровно та подделка,
    # от которой должна защищать проверка hash
    forged = init_data.replace("Friend", "Intruder")

    with pytest.raises(InitDataError):
        validate_init_data(forged, bot_token=BOT_TOKEN)


def test_wrong_bot_token_is_rejected() -> None:
    init_data = sign_init_data(valid_fields(), bot_token=BOT_TOKEN)

    with pytest.raises(InitDataError):
        validate_init_data(init_data, bot_token="other-token")


def test_missing_hash_is_rejected() -> None:
    init_data = urlencode(valid_fields())

    with pytest.raises(InitDataError):
        validate_init_data(init_data, bot_token=BOT_TOKEN)


def test_expired_auth_date_is_rejected() -> None:
    old = int(time.time()) - 7200
    init_data = sign_init_data(valid_fields(auth_date=old))

    with pytest.raises(InitDataError):
        validate_init_data(init_data, bot_token=BOT_TOKEN, max_age_seconds=3600)


def test_fresh_auth_date_within_window_is_accepted() -> None:
    recent = int(time.time()) - 10
    init_data = sign_init_data(valid_fields(auth_date=recent))

    validate_init_data(init_data, bot_token=BOT_TOKEN, max_age_seconds=3600)  # must not raise


def test_missing_user_field_is_rejected() -> None:
    fields = {"auth_date": str(int(time.time()))}
    init_data = sign_init_data(fields)

    with pytest.raises(InitDataError):
        validate_init_data(init_data, bot_token=BOT_TOKEN)


def test_malformed_user_json_is_rejected() -> None:
    fields = {"auth_date": str(int(time.time())), "user": "not-json"}
    init_data = sign_init_data(fields)

    with pytest.raises(InitDataError):
        validate_init_data(init_data, bot_token=BOT_TOKEN)
