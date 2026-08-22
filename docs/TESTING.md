# Тестирование

```
make test         # unit-тесты, без базы и сети
```

## Структура тестов

- `tests/unit/` — домен, application (на фейковых портах, `tests/unit/application/fakes.py`),
  presentation; без базы и сети.
- `tests/integration/grpc/` — контрактные тесты `SpiritVPNGateway` против
  реального `spiritvpnd`.
- `tests/integration/postgres/` — тесты Postgres-слоя (репозитории,
  `SqlAlchemyUnitOfWork`, блокировка строк), отдельный гейт.

## Postgres-интеграционные тесты

Не пересекаются с конфигурацией самого процесса (`BOT_DATABASE_URL`) —
собственный гейт и своя переменная адреса БД:

```
BOT_INTEGRATION_TESTS=1 DATABASE_URL="postgresql+asyncpg://spiritvpn_bot:spiritvpn_bot@localhost:5434/spiritvpn_bot" \
  poetry run pytest tests/integration/postgres
```

Без `BOT_INTEGRATION_TESTS=1` эти тесты пропускаются — обычный `make test`
их не запускает и не требует локального Postgres.

## Локальные проверки перед коммитом

`pre-commit install` один раз, дальше хуки запускаются автоматически
(`ruff`, `ruff format`). `mypy` в хуки не входит — только в CI.

## Что гоняет CI (`.github/workflows/ci.yml`)

На каждый push и pull request в `Develop`:

- **test** — `pytest --cov=spiritvpn_bot`, с реальным Postgres как сервисом
  GitHub Actions (`BOT_INTEGRATION_TESTS=1` выставлен, интеграционные тесты
  участвуют), порог покрытия — 80% строк, миграции накатываются перед
  запуском (`alembic upgrade head`).
- **lint** — `ruff check`, `ruff format --check`, `mypy -p spiritvpn_bot`.

Подробнее о том, что происходит после зелёного `test`+`lint` (сборка и
публикация образа) — в [Развёртывании](DEPLOYMENT.md).

## Конвенции

- Порты в тестах — фейки (`tests/unit/application/fakes.py`), не моки:
  `InMemoryOrderRepository` и т.д. реализуют тот же `Protocol`, что и
  реальный адаптер.
- Пути API-эндпоинтов в тестах — литеральные строки (`"/api/me/links"`),
  а не билдеры/именованные роуты — стандартная практика для FastAPI-тестов
  такого масштаба, а не отступление от неё.
- Регрессионные тесты добавляются на каждый живой баг, а не только на
  фичи — например, `test_error_sink_never_reuses_the_main_bot_token`
  закрепляет архитектурное ограничение (см.
  [Конфигурацию](CONFIGURATION.md#error)), а не поведение по умолчанию.
