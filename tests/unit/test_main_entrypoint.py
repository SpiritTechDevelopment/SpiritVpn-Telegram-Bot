from __future__ import annotations

import pytest

from spiritvpn_bot import logging as logging_module
from spiritvpn_bot.__main__ import _setup_error_sink
from spiritvpn_bot.config import Settings
from spiritvpn_bot.logging import set_error_sink

_REQUIRED_ENV = {
    "BOT_TELEGRAM_BOT_TOKEN": "main-bot-token",
    "BOT_DATABASE_URL": "postgresql+asyncpg://x",
    "BOT_SPIRITVPND_GRPC_TARGET": "x:1",
    "BOT_SPIRITVPND_TLS_CLIENT_CERT_FILE": "x",
    "BOT_SPIRITVPND_TLS_CLIENT_KEY_FILE": "x",
    "BOT_SPIRITVPND_TLS_CA_FILE": "x",
    "BOT_SUBSCRIPTION_BASE_URL": "https://x",
    "BOT_MINI_APP_URL": "https://x",
    "BOT_SUBSCRIPTION_SIGNING_KEY": "x",
    "BOT_FRIENDS_PLAN_FLEET_ID": "1",
    "BOT_FRIENDS_SHARED_CODE": "x",
}


@pytest.fixture
def load_settings_from_env(monkeypatch: pytest.MonkeyPatch):
    """Проверка загрузки объекта Settings из энвов окружения"""
    for key, value in _REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)

    def _load(**extra_env: str) -> Settings:
        for key, value in extra_env.items():
            monkeypatch.setenv(key, value)
        return Settings(_env_file=None)  # type: ignore[call-arg]

    return _load


@pytest.fixture(autouse=True)
def _reset_error_sink():
    yield
    set_error_sink(None)


def test_error_sink_disabled_without_chat_id_and_dedicated_token(load_settings_from_env) -> None:
    _setup_error_sink(load_settings_from_env())

    assert logging_module._error_sink is None


def test_error_sink_disabled_when_only_chat_id_is_set(load_settings_from_env) -> None:
    settings = load_settings_from_env(TELEGRAM_CHAT_ID="-100123")

    _setup_error_sink(settings)

    assert logging_module._error_sink is None


def test_error_sink_never_reuses_the_main_bot_token(load_settings_from_env) -> None:
    settings = load_settings_from_env(
        TELEGRAM_CHAT_ID="-100123",
        TELEGRAM_BOT_TOKEN="987654321:dedicated-error-bot-token",
    )

    _setup_error_sink(settings)

    assert logging_module._error_sink is not None
    assert logging_module._error_sink._bot.token == "987654321:dedicated-error-bot-token"
