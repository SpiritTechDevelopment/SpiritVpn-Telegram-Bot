# Конфигурация

Полный список переменных — в `.env.example` в корне репозитория; отсутствие
переменной там или расхождение с `config.py` ловит
`tests/unit/test_env_example.py`. Для запуска скопируйте файл в `.env` и
заполните.

## Требования

- Python 3.11–3.13, Poetry 2.x
- Docker с плагином Compose — локальный Postgres
- `openssl` — dev-сертификаты для локального `spiritvpnd`, если он нужен

## Быстрый старт

```
make install      # poetry install
make proto-gen     # сгенерировать gRPC-стабы из proto/
make dev-db        # локальный Postgres на :5434
```

Накатить схему:

```
BOT_DATABASE_URL="postgresql+asyncpg://spiritvpn_bot:spiritvpn_bot@localhost:5434/spiritvpn_bot" \
  poetry run alembic upgrade head
```

Запуск процессов:

```
poetry run python -m spiritvpn_bot bot   # long polling
poetry run python -m spiritvpn_bot api   # mini app + /s/{token}
```

## Переменные окружения

Основные (префикс `BOT_`):

| Переменная | Назначение |
|---|---|
| `BOT_TELEGRAM_BOT_TOKEN` | токен основного бота, выдаётся BotFather |
| `BOT_LOG_LEVEL` | необязательная, уровень логирования, по умолчанию `INFO` |
| `BOT_DATABASE_URL` | адрес собственной БД бота (не БД `spiritvpnd`) |
| `BOT_SPIRITVPND_GRPC_TARGET` | адрес `spiritvpnd`, `host:port` |
| `BOT_SPIRITVPND_TLS_CLIENT_CERT_FILE` / `_KEY_FILE` / `BOT_SPIRITVPND_TLS_CA_FILE` | mTLS-сертификаты клиента к `spiritvpnd` |
| `BOT_SUBSCRIPTION_BASE_URL` | публичный адрес процесса `api`, для ссылок `/s/{token}` |
| `BOT_MINI_APP_URL` | публичный адрес мини-аппа для кнопки в боте |
| `BOT_MINI_APP_HTTP_PORT` | необязательная, порт процесса `api`, по умолчанию 8080 |
| `BOT_SUBSCRIPTION_SIGNING_KEY` | секрет подписи токена `/s/{token}` |
| `BOT_FRIENDS_PLAN_FLEET_ID` | `vpn_fleet_id` бесплатного плана, должен существовать в манифесте `spiritvpnd` |
| `BOT_FRIENDS_PLAN_QUOTA_BYTES` | необязательная, квота трафика на ноду для бесплатного плана |
| `BOT_FRIENDS_PLAN_DURATION_DAYS` | необязательная, срок действия бесплатного плана в днях |
| `BOT_FRIENDS_SHARED_CODE` | общий пароль для бесплатного доступа |

`BOT_SUBSCRIPTION_BASE_URL` и `BOT_MINI_APP_URL` обязаны быть публичным
`https`-адресом: Telegram отклоняет инлайн-кнопки на `localhost` и на любой
недоступный ему адрес целиком, вместе с сообщением. Для локальной разработки
без деплоя — туннель (`cloudflared tunnel --url http://localhost:$PORT`).

### Уведомления об ошибках в Telegram {#error}

Пересылка логов уровня `error`/`exception` в топик Telegram — тот же общий
топик ошибок, что использует `SpiritVPN` (бэкенд) и `Infrastructure`.
Поэтому переменные **без префикса `BOT_`** — те же самые имена, что и у
остальных сервисов, чтобы один и тот же секрет можно было раздать во все
сервисы без дублирования:

| Переменная | Назначение |
|---|---|
| `TELEGRAM_CHAT_ID` | chat_id топика/группы. Не задан — уведомления выключены целиком |
| `TELEGRAM_BOT_TOKEN` | токен **отдельного** бота для уведомлений об ошибках |
| `BOT_ERROR_NOTIFICATIONS_MESSAGE_THREAD_ID` | необязательная, `message_thread_id` топика внутри группы, если это форум |

Важное архитектурное ограничение: основной бот (`BOT_TELEGRAM_BOT_TOKEN`)
**никогда** не используется для отправки уведомлений об ошибках, даже как
запасной вариант, даже если `TELEGRAM_BOT_TOKEN` не задан. Не заданы
`TELEGRAM_CHAT_ID` или `TELEGRAM_BOT_TOKEN` — уведомления тихо выключаются
целиком (`_setup_error_sink()` в `__main__.py`), это осознанное решение, а
не заглушка на будущее. Само подключение к TelegramErrorSink рассчитано так,
чтобы сбой отправки уведомления никогда не ронял процесс и не маскировал
исходную ошибку (`_safe_send()` глушит все исключения при отправке).

Проверено регрессионным тестом
(`tests/unit/test_main_entrypoint.py::test_error_sink_never_reuses_the_main_bot_token`).

## Выдача бесплатного доступа

Клиент отправляет боту текстом значение `BOT_FRIENDS_SHARED_CODE`. Пароль
общий, не персональный; отозвать доступ одному клиенту нельзя — только
сменить пароль для всех разом.

## Локальный `spiritvpnd`

Для полного end-to-end теста (включая реальный вызов `ApplyCustomerAccess`)
нужен запущенный `spiritvpnd` и манифест с флотом, на который ссылается
`BOT_FRIENDS_PLAN_FLEET_ID`. Порядок действий — в README репозитория
`SpiritVPN`, раздел «Быстрый старт» (`make dev`, `make dev-certs`, запуск
`cmd/spiritvpnd`). Манифест применяется вызовом `ApplyFleetManifest` с ролью
`manifest-writer`.

Без реального узла (Xray-агента) доступ будет подтверждён на уровне
`spiritvpnd`, но ссылка останется в состоянии `PENDING` — доставлять доступ
физически некуда.
