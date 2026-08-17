# SpiritVPN Bot

Telegram-бот и mini app, которые продают доступ к SpiritVPN (VLESS + REALITY).
Общаются с бэкендом `spiritvpnd` по gRPC/mTLS как его «product-сервис»: решают,
кому какой флот положен, а как это доехало до ноды — уже забота `spiritvpnd`.

## Структура

Domain-first, ports & adapters, в том же стиле, что и сам `spiritvpnd`:

- `src/spiritvpn_bot/domain/` — сущности и правила, без ввода-вывода. Здесь
  живёт машина состояний `Order` и правило монотонности `command_number`.
- `src/spiritvpn_bot/application/` — use case'ы и `Protocol`-порты, от которых
  они зависят (`OrderRepository`, `VPNAccessGateway`, `UnitOfWork`, ...).
- `src/spiritvpn_bot/infrastructure/spiritvpn_grpc/` — mTLS-клиент к
  spiritvpnd (`client.py`) и `SpiritVPNGateway` (`gateway.py`), реализующий
  `VPNAccessGateway`: единственное место, где существуют protobuf-типы и коды
  `grpc.StatusCode`. Postgres и платёжные провайдеры пока не собраны.
- `src/spiritvpn_bot/presentation/` — aiogram-бот, FastAPI мини-аппа и
  публичный эндпоинт подписки (`/s/{token}`). Пока не собраны.
- `proto/spiritvpn/customer/v1/customer.proto` — вендоренный контракт из
  репозитория SpiritVPN. `src/spiritvpn/` — сгенерированные из него
  gRPC-стабы (`make proto-gen`); отдельный top-level пакет, не трогать руками.
- `tests/unit/` — тесты домена и application-слоя: без базы, без сети,
  самописные фейки (`tests/unit/application/fakes.py`) вместо
  моко-библиотеки — журнал вызовов фейка позволяет проверять порядок
  операций, а не только факт вызова.
- `tests/integration/grpc/` — контрактные тесты `SpiritVPNGateway` против
  in-process gRPC-сервера на сгенерированных классах: ловят рассинхрон с
  контрактом на этапе импорта, без staging spiritvpnd и без mTLS.

## Быстрый старт

```
make install     # poetry install
make proto-gen    # сгенерировать gRPC-стабы из proto/
make dev-db       # локальный Postgres на :5434 для разработки и тестов
make test         # тесты (постгреса пока не требуют)
```

Скопируйте `.env.example` в `.env` и заполните значения по мере готовности
соответствующих частей (токен бота, mTLS-сертификат/ключ/CA для spiritvpnd,
адрес базы). Для dev-сертификатов к spiritvpnd — `make dev-certs` в
репозитории SpiritVPN; идентичность клиента там `product-svc`.

## CI/CD

`.github/workflows/ci.yml`, три job'а, по образцу SpiritVPN и NodeAgent:

- **test** — `pytest` с покрытием, гейт 80% (сейчас ~89%);
- **lint** — `ruff check`, `ruff format --check`, `mypy -p spiritvpn_bot`;
- **images** — только на push в `Develop`, после test и lint: собирает
  `Dockerfile` и пушит в `ghcr.io/spirittechdevelopment/spiritvpn-bot`, тег
  `sha-<commit>`. Один тег, без плавающего `develop`/`latest` — та же причина,
  что у NodeAgent: identity деплоя несёт digest, а не тег, а второй тег только
  создаёт риск разъехаться.

Локально те же проверки — `pre-commit install` один раз, дальше хуки идут
сами при коммите (`.pre-commit-config.yaml`: hygiene-хуки + `ruff`/`ruff format`;
`mypy` в pre-commit намеренно не включён, он остаётся в CI — слишком медленный
для докоммитного хука).

### Чего не хватает для реальной выкатки

Этот репозиторий публикует образ и останавливается — так же, как и
`spiritvpnd`: «какая версия работает в среде» решает `Infrastructure`, не мы.
Но, в отличие от `spiritvpnd`, для бота там пока нет принимающей стороны:

- mTLS-идентичность **уже зарезервирована**: `desired/environments/develop/environment.yml`
  перечисляет `spiffe://spiritvpn/develop/service/customer-service` в
  `customer_access_writers`/`customer_access_readers`, и в
  `fleetctl/pki/model.py` есть профиль сертификата `customer-service` — то
  есть PKI готова выдать нам клиентский сертификат уже сейчас;
- но в `environment.yml` нет секции под сам компонент (аналога `control:` для
  spiritvpnd), нет Ansible-роли, которая бы его запускала, и нет workflow,
  принимающего `repository_dispatch` с образом бота — то, что у backend'а
  называется `notify-infrastructure` (`SpiritVPN/.github/workflows/ci.yml`).

Это работа в `Infrastructure`, не здесь — заводить `notify-infrastructure` в
этом репозитории раньше, чем там появится принимающая сторона, означало бы
дописать шаг, который дёргает несуществующий обработчик. Как только в
`Infrastructure` заведут секцию компонента и роль — добавить сюда финальный
job по образцу `SpiritVPN/.github/workflows/ci.yml:367` займёт пару минут.

## Статус

Domain и application слои существуют и покрыты тестами. Собран и
протестирован контрактными тестами gRPC-клиент к spiritvpnd
(`CustomerAccessService`). Настроен CI/CD: тесты, линт, публикация образа в
ghcr.io. Пока не собраны: адаптеры Postgres, платёжный провайдер (Telegram
Stars), хендлеры aiogram, FastAPI мини-аппа, эндпоинт подписки и фоновые
воркеры.
