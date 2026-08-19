# SpiritVPN Bot

Telegram-бот и mini app для продажи доступа к SpiritVPN (VLESS + REALITY).
Сервис является product-клиентом бэкенда `spiritvpnd`: обращается к нему по
gRPC/mTLS, чтобы выдавать и проверять доступ клиентов. P.S. Данный бот вообще хуй кладет на доставку доступа на ноды, т.к это зона отевтственности `spiritvpnd`.

## Требования

- Python 3.11–3.13, Poetry 2.x
- Docker с плагином Compose — локальный Postgres
- `openssl` — dev-сертификаты для локального `spiritvpnd`, если он нужен

## Структура

Layer архитектура (ports & adapters):

- `src/spiritvpn_bot/domain/` — сущности и бизнес-правила, без ввода-вывода.
  Машина состояний `Order`, правило монотонности `command_number`.
- `src/spiritvpn_bot/application/` — use case'ы и `Protocol`-порты
  (`OrderRepository`, `VPNAccessGateway`, `UnitOfWork`).
- `src/spiritvpn_bot/infrastructure/spiritvpn_grpc/` — mTLS-клиент к
  `spiritvpnd` и `SpiritVPNGateway`, реализующий `VPNAccessGateway`.
- `src/spiritvpn_bot/infrastructure/postgres/` — SQLAlchemy 2.0 async:
  модели, `SqlAlchemyUnitOfWork`, репозитории.
- `src/spiritvpn_bot/presentation/telegram_bot/` — aiogram-хендлеры.
  `/start` — приветствие и кнопка мини-аппа. Бесплатный доступ
  выдаётся по общему паролю (`RedeemFriendCodeUseCase`): любое текстовое
  сообщение молча проверяется на совпадение, при несовпадении бот отвечает
  так же, как на любой другой непонятный текст.
- `src/spiritvpn_bot/presentation/mini_app_api/` — FastAPI: подписочная
  ссылка (`/s/{token}`), статус доступа и каталог тарифов для мини-аппа,
  статическая страница интерфейса (`static/index.html`).
- `src/spiritvpn_bot/di.py` — композиционный корень.
- `proto/`, `src/spiritvpn/` — вендоренный `.proto`-контракт и
  сгенерированные из него gRPC-стабы (`make proto-gen`).
- `migrations/` — Alembic-миграции.
- `tests/unit/` — домен, application, presentation; без базы и сети.
- `tests/integration/grpc/` — контрактные тесты `SpiritVPNGateway`.
- `tests/integration/postgres/` — тесты Postgres-слоя, гейт
  `BOT_INTEGRATION_TESTS` + `DATABASE_URL`.

## Конфигурация

Полный список переменных — в `.env.example`; отсутствие или расхождение с
`config.py` ловит `tests/unit/test_env_example.py`. Для запуска скопируйте
файл в `.env` и заполните:

| Переменная | Назначение |
|---|---|
| `BOT_TELEGRAM_BOT_TOKEN` | токен бота, выдаётся BotFather |
| `BOT_DATABASE_URL` | адрес собственной БД бота (не БД `spiritvpnd`) |
| `BOT_SPIRITVPND_GRPC_TARGET` | адрес `spiritvpnd`, `host:port` |
| `BOT_SPIRITVPND_TLS_CLIENT_CERT_FILE` / `_KEY_FILE` / `BOT_SPIRITVPND_TLS_CA_FILE` | mTLS-сертификаты клиента к `spiritvpnd` |
| `BOT_SUBSCRIPTION_BASE_URL` | публичный адрес процесса `api`, для ссылок `/s/{token}` |
| `BOT_MINI_APP_URL` | публичный адрес мини-аппа для кнопки в боте |
| `BOT_MINI_APP_HTTP_PORT` | порт процесса `api`, по умолчанию 8080 |
| `BOT_SUBSCRIPTION_SIGNING_KEY` | секрет подписи токена `/s/{token}` |
| `BOT_FRIENDS_PLAN_FLEET_ID` | `vpn_fleet_id` бесплатного плана, должен существовать в манифесте `spiritvpnd` |
| `BOT_FRIENDS_SHARED_CODE` | общий пароль для бесплатного доступа |

`BOT_SUBSCRIPTION_BASE_URL` и `BOT_MINI_APP_URL` обязаны быть публичным
`https`-адресом: Telegram отклоняет инлайн-кнопки на `localhost` и на любой
недоступный ему адрес целиком, вместе с сообщением. Для локальной разработки
без деплоя — туннель (`cloudflared tunnel --url http://localhost:$PORT`).

## Быстрый старт

```
make install     # poetry install
make proto-gen    # сгенерировать gRPC-стабы из proto/
make dev-db       # локальный Postgres на :5434
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

Выдача бесплатного доступа: клиент отправляет боту текстом значение
`BOT_FRIENDS_SHARED_CODE`. Пароль общий, не персональный; отозвать доступ
одному клиенту нельзя — только сменить пароль для всех разом.

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

## Тестирование

```
make test         # unit-тесты, без базы
```

Postgres-интеграционные тесты — отдельный гейт, не пересекается с
конфигурацией процесса:

```
BOT_INTEGRATION_TESTS=1 DATABASE_URL="postgresql+asyncpg://spiritvpn_bot:spiritvpn_bot@localhost:5434/spiritvpn_bot" \
  poetry run pytest tests/integration/postgres
```

Локальные проверки перед коммитом — `pre-commit install` один раз, дальше
хуки запускаются автоматически (`ruff`, `ruff format`; `mypy` — только в CI).

## Git-флоу и релизы

Основная ветка — `Develop`. Изменения вносятся через отдельную ветку и
pull request в `Develop`; прямые пуши в `Develop` допустимы только до прод этапа
На каждый push и pull request запускается `test` и `lint`
(`.github/workflows/ci.yml`). После их успешного прохождения push в `Develop`
дополнительно собирает образ и публикует его в
`ghcr.io/spirittechdevelopment/spiritvpn-bot` с тегом `sha-<commit>`. Плавающего
тега (`latest`, `develop`) нет: идентичность образа для деплоя — digest, а не
тег.

Продвижение образа в прод (по тегу `v*`, как у `SpiritVPN`) не реализовано —
целевого prod-окружения для бота пока нет.

### Выкатка

Репозиторий публикует образ и на этом останавливается. Какая версия
работает в среде, решает `Infrastructure`, не этот репозиторий. Для бота
там пока нет принимающей стороны:

- mTLS-идентичность зарезервирована: `spiffe://spiritvpn/develop/service/customer-service`
  указана в `desired/environments/develop/environment.yml`
  (`customer_access_writers`/`customer_access_readers`); профиль сертификата
  `customer-service` есть в `fleetctl/pki/model.py`.
- В `environment.yml` нет секции под сам компонент, нет Ansible-роли для его
  запуска и нет workflow, принимающего `repository_dispatch` с образом бота
  (у `spiritvpnd` это `notify-infrastructure`).

Добавление `notify-infrastructure` в этот репозиторий имеет смысл после
того, как в `Infrastructure` появится секция компонента, роль и обработчик
события.

#### mTLS до spiritvpnd

Бот — клиент, не эмитент сертификатов: он только читает готовые PEM-файлы
с диска (`infrastructure/spiritvpn_grpc/client.py`), сам ничего не выпускает
и не запрашивает. Пока никто не выпустил и не доставил эти файлы,
подключение к `spiritvpnd` падает на TLS-хендшейке — это ожидаемо и не
связано с кодом бота. Для развёрнутого (не локального) `spiritvpnd`
`Infrastructure` должна положить в окружение бота:

| Переменная | Содержимое |
|---|---|
| `BOT_SPIRITVPND_GRPC_TARGET` | `host:port` того `spiritvpnd`, к которому подключается бот |
| `BOT_SPIRITVPND_TLS_CLIENT_CERT_FILE` | клиентский сертификат identity `spiffe://spiritvpn/develop/service/customer-service`, выпущенный `fleetctl` по профилю `customer-service` (`fleetctl/pki/model.py`) |
| `BOT_SPIRITVPND_TLS_CLIENT_KEY_FILE` | приватный ключ этого сертификата |
| `BOT_SPIRITVPND_TLS_CA_FILE` | CA, которым подписан серверный сертификат самого `spiritvpnd` (это не обязательно тот же CA, что подписывает identity бота) |

Профиль `customer-service` в `fleetctl` зарезервирован, но пока никем не
выпускался под конкретное окружение — это первый шаг, без которого
остальная выкатка (Ansible-роль, `environment.yml`) не имеет смысла
проверять.

## Статус

Реализовано: бесплатная выдача доступа по общему паролю, end-to-end, и
мини-апп как основной интерфейс. Домен, application и Postgres-слой
покрыты тестами, включая интеграционные тесты на блокировке строк.
gRPC-клиент к `spiritvpnd` покрыт контрактными тестами. CI/CD публикует
образ в `ghcr.io`.

Не реализовано: платные планы и оплата (в каталоге только `friends-free`,
кнопка «Купить» в мини-аппе не завершает покупку), фоновые воркеры
(напоминание об истечении подписки, синхронизация статуса), продвижение
образа в прод, приёмная сторона в `Infrastructure`.
