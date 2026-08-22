# API мини-аппа

FastAPI-процесс (`python -m spiritvpn_bot api`), собирается в
`presentation/mini_app_api/main.py:create_app()`. Раздаёт саму статическую
страницу мини-аппа (`/`) и JSON/текстовые эндпоинты, которые эта страница
опрашивает через `fetch`.

## Аутентификация

Эндпоинты `/api/*` требуют заголовок `X-Telegram-Init-Data` — сырые
`initData` из Telegram WebApp. Подпись проверяется (`auth.py`) против
`BOT_TELEGRAM_BOT_TOKEN`; из проверенных данных извлекается `customer_id`.
Без заголовка или с неверной подписью — `401`.

## Эндпоинты

| Метод и путь | Назначение |
|---|---|
| `GET /health` | health-check процесса |
| `GET /s/{token}` | подписочная ссылка: отдаёт содержимое подписки текстом по подписанному токену (`SubscriptionTokenSigner`) |
| `GET /api/me/links` | текущие ссылки клиента вида BRIDGE (`GetMyLinksUseCase` отфильтровывает FREEDOM) |
| `GET /api/me/subscription-status` | `{"days_left": int \| null}` — остаток срока подписки; `null`, если у клиента нет заказов |
| `GET /api/me/subscription-url` | публичный URL `/s/{token}` этого клиента |
| `GET /api/plans` | каталог тарифов для витрины (`PlanCatalog.purchasable()`) |
| `GET /` | статическая страница мини-аппа (`static/index.html`) |

### `GET /api/me/links`

Отвечает `list[LinkStatusOut]` — по одной записи на ссылку клиента, только
вида BRIDGE: `GetMyLinksUseCase` отбрасывает FREEDOM, клиенту продукта он не
показывается и не выдаётся. Поля `kind` в ответе нет — раз он теперь всегда
один и тот же, толку в нём клиенту нет.

### `GET /api/me/subscription-status`

Источник для чипа «дней осталось» в интерфейсе мини-аппа. Берётся заказ
клиента с максимальным `command_number` (реально применённая в `spiritvpnd`
выдача), `days_left = max(0, (expires_at - now).days)`.

### `GET /api/plans`

Только `purchasable`-планы (сейчас `paid-1m`, `paid-3m`) — `friends-free`
в публичную витрину не попадает, он выдаётся отдельно через общий пароль
в боте. У каждого плана — `display_as_unlimited`, при `true` интерфейс
показывает «Безлимит» вместо количества гигабайт в квоте.

Покупка (`POST`-эндпоинт, оплата) пока не реализована — см.
[Roadmap](ROADMAP.md); кнопка «Купить» в интерфейсе её не завершает.
