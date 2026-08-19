"""Гарантирует, что .env.example не расходится с Settings.

Ручная синхронизация двух списков переменных — источник дрейфа: поле в
config.py легко добавить и забыть дописать в .env.example, и следующий, кто
разворачивает бота с нуля, ловит невнятную ошибку валидации pydantic вместо
понятного списка того, что нужно заполнить.
"""

from __future__ import annotations

import re
from pathlib import Path

from spiritvpn_bot.config import Settings

_ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"
_KEY_PATTERN = re.compile(r"^#?\s*(BOT_[A-Z0-9_]+)=", re.MULTILINE)


def _keys_in_env_example() -> set[str]:
    text = _ENV_EXAMPLE.read_text(encoding="utf-8")
    return set(_KEY_PATTERN.findall(text))


def _uncommented_keys_in_env_example() -> set[str]:
    text = _ENV_EXAMPLE.read_text(encoding="utf-8")
    return {
        match.group(1)
        for match in re.finditer(r"^(BOT_[A-Z0-9_]+)=", text, re.MULTILINE)
    }


def test_every_setting_is_documented() -> None:
    expected = {f"BOT_{name.upper()}" for name in Settings.model_fields}
    documented = _keys_in_env_example()
    missing = expected - documented
    assert not missing, f".env.example не упоминает: {sorted(missing)}"


def test_env_example_has_no_stray_keys() -> None:
    # обратная проверка: не даёт .env.example накопить переменные, которых
    # в Settings уже нет — типичный след недоведённого до конца рефакторинга
    expected = {f"BOT_{name.upper()}" for name in Settings.model_fields}
    documented = _keys_in_env_example()
    stray = documented - expected
    assert not stray, f".env.example упоминает несуществующие переменные: {sorted(stray)}"


def test_required_settings_are_not_commented_out() -> None:
    required = {
        f"BOT_{name.upper()}"
        for name, field in Settings.model_fields.items()
        if field.is_required()
    }
    uncommented = _uncommented_keys_in_env_example()
    missing = required - uncommented
    assert not missing, f".env.example закомментировал обязательные переменные: {sorted(missing)}"
