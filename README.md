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

## Статус

Domain и application слои существуют и покрыты тестами. Собран и
протестирован контрактными тестами gRPC-клиент к spiritvpnd
(`CustomerAccessService`). Пока не собраны: адаптеры Postgres, платёжный
провайдер (Telegram Stars), хендлеры aiogram, FastAPI мини-аппа, эндпоинт
подписки и фоновые воркеры.
