# Архитектура

Layer-архитектура (ports & adapters / гексагональная): зависимости идут
внутрь, к `domain`, через `Protocol`-порты в `application`; `infrastructure`
и `presentation` — заменяемые адаптеры вокруг этого ядра.

```
domain          — сущности и бизнес-правила, без ввода-вывода
  ↑
application     — use case'ы + Protocol-порты (OrderRepository, VPNAccessGateway, UnitOfWork, ...)
  ↑
infrastructure  — конкретные реализации портов (Postgres, gRPC, Telegram, логи)
presentation    — aiogram-бот и FastAPI mini app, оба поверх application
```

## domain

`src/spiritvpn_bot/domain/`

- `entities/order.py` — машина состояний `Order`: `DRAFT` →
  `AWAITING_PAYMENT` → `PAID` (после этого `command_number` и `expires_at`
  зафиксированы). `command_number` монотонно растёт — это правило проверяет
  сам домен, а не репозиторий.
- `entities/plan.py` — `Plan`: тариф (`fleet_id`, `duration_days`,
  `quota_bytes`, `price`, `purchasable`, `display_as_unlimited`).
  `display_as_unlimited` — только отображение в интерфейсе, на реальную
  `quota_bytes`, которая уходит в `spiritvpnd`, не влияет.
- `entities/money.py` — `Money` (сумма + валюта).
- `events.py` — доменные события (`OrderPaid`).
- `services/` — доменные правила, не привязанные к одной сущности.

## application

`src/spiritvpn_bot/application/`

- `use_cases/` — один класс на сценарий, конструктор принимает порты,
  `execute()` — единственный публичный метод:
  - `redeem_friend_code.py` — выдача бесплатного доступа по общему паролю
    (`RedeemFriendCodeUseCase`); там же тест-коды (`test10m`/`test1h`/
    `test1w`/`test1mo`) для ручной проверки коротких сроков жизни — см.
    [FAQ](FAQ.md).
  - `request_vpn_access.py` — заявка на доступ к VPN (`RequestAccessUseCase`),
    вызывает `spiritvpnd` через `VPNAccessGateway`.
  - `get_my_links.py` — текущие ссылки клиента для мини-аппа, только вида
    BRIDGE (`GetMyLinksUseCase` отфильтровывает FREEDOM — внутренний kind
    spiritvpnd, не часть продуктового контракта).
  - `get_subscription_status.py` — остаток срока подписки в днях
    (`GetSubscriptionStatusUseCase`), на основе заказа с максимальным
    `command_number`.
  - `purchase_subscription.py` / `confirm_payment.py` — создание заказа
    (`AWAITING_PAYMENT`) и фиксация оплаты (`PAID` + `command_number` +
    публикация `OrderPaid`). Оба use case'а собраны и покрыты тестами, но
    **не подключены** ни к одному хендлеру или роуту — интеграции с
    платёжным провайдером ещё нет, см. [Roadmap](ROADMAP.md).
  - `_shared.py` — `assign_command_number_and_mark_paid()`, общая для
    `redeem_friend_code` и `confirm_payment` логика выдачи номера команды.
- `builders/` — `OrderBuilder`, `SubscriptionContentBuilder` — сборка
  сущностей и подписочного контента без бизнес-правил внутри use case'а.
- `ports/` — `Protocol`-интерфейсы: `OrderRepository`, `VPNAccessGateway`,
  `UnitOfWork`, `Clock`, `IdGenerator`, `EventPublisher`, `UpdatesGuard`.
- `plans.py` — `PlanCatalog`, собирается в рантайме из настроек
  (`build_plan_catalog()`): один бесплатный план (`friends-free`) и два
  платных (`paid-1m`, `paid-3m`) — у платных `fleet_id` временно совпадает
  с `fleet_id` бесплатного плана (`# TODO` в коде), реальный флот тарифов
  ещё не заведён в манифесте `spiritvpnd`.
- `errors.py` — доменные/application-исключения (`OrderNotFound`,
  `PlanNotFound`, `ExpiryRegression`, ...), presentation мапит их в
  понятные ответы пользователю.

## infrastructure

`src/spiritvpn_bot/infrastructure/`

- `spiritvpn_grpc/` — mTLS gRPC-клиент к `spiritvpnd` и `SpiritVPNGateway`
  (реализация `VPNAccessGateway`).
- `postgres/` — SQLAlchemy 2.0 async: модели, `SqlAlchemyUnitOfWork`,
  репозитории. **Не singleton**: `di.py` создаёт новый `UnitOfWork` на
  каждый вызов use case'а — `SqlAlchemyUnitOfWork` не безопасен для
  параллельного переиспользования.
- `telegram_error_sink.py` — `TelegramErrorSink`, пересылает
  error/exception-логи в топик Telegram, см. [Конфигурацию](CONFIGURATION.md#error).
- `events/logging_publisher.py` — `LoggingEventPublisher`, реализация
  `EventPublisher` по умолчанию: публикует доменные события в
  структурированный лог (не в брокер сообщений — его пока нет).
- `payments/` — зарезервировано под адаптер платёжного провайдера, сейчас
  пусто.

## presentation

`src/spiritvpn_bot/presentation/`

- `telegram_bot/` — aiogram-приложение:
  - `texts.py` — весь копирайтинг бота (тексты сообщений, подписи кнопок,
    шаблоны) в одном месте, отдельно от логики хендлеров — сюда и правится
    текст, не трогая `handlers/`.
  - `handlers/start.py` — `/start` (зацикленная GIF-анимация приветствия +
    кнопки приложения/поддержки/отзывов), `/status`, `/plans`, `/support`,
    `/help`, обработка
    текстовых сообщений (проверка на общий пароль / тест-код), маппинг
    `ExpiryRegression` и прочих ошибок в понятный ответ клиенту. Там же —
    скрытая (не в `/help`, не в меню бота) dev-команда
    `create_<минуты>_<байты>`: строгий формат, работает только для id из
    `BOT_DEV_ADMIN_USER_IDS`, для всех остальных падает в обычный флоу
    неотличимо от любого другого текста (см. `CreateDevAccessLinkUseCase`).
  - `middlewares/dedup.py` — `DedupUpdatesMiddleware`: защита от повторной
    обработки одного и того же Telegram `update_id`
    (Postgres-backed `UpdatesGuard`) — актуально при `getUpdates`
    long polling, где офсет подтверждается только следующим запросом.
  - `keyboards/` — inline-клавиатуры (кнопка мини-аппа и т.д.).
- `mini_app_api/` — FastAPI-процесс:
  - `main.py` — `create_app()`, все роуты, см. [API](API.md).
  - `auth.py` — проверка `X-Telegram-Init-Data` (подпись Telegram
    WebApp init data).
  - `schemas.py` — Pydantic-схемы ответов.
  - `static/index.html` — интерфейс мини-аппа: одна статическая страница
    (без фронтенд-сборки), тянет данные с `/api/*` через `fetch`.
- `subscription_api/` — зарезервировано; сейчас `/s/{token}` обслуживается
  из `mini_app_api`, отдельный процесс не выделен.

## Композиционный корень

`src/spiritvpn_bot/di.py` — `Container` и `build_container(settings)`.
Для use case'ов, использующих `UnitOfWork`, — фабричные методы
(`purchase_subscription_use_case()`, `redeem_friend_code_use_case()`, ...),
не готовые инстансы: каждый вызов создаёт свежий `UnitOfWork`.

## Прочее

- `proto/`, `src/spiritvpn/` — вендоренный `.proto`-контракт и
  сгенерированные из него gRPC-стабы (`make proto-gen`).
- `migrations/` — Alembic-миграции.
- `src/spiritvpn_bot/logging.py` — единственная точка входа в `structlog`
  в проекте: `configure_logging()` / `get_logger()`; остальной код
  `structlog` напрямую не импортирует.
