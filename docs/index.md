# SpiritVPN Bot

[![CI/CD Pipeline](https://github.com/SpiritTechDevelopment/SpiritVpn-Telegram-Bot/actions/workflows/ci.yml/badge.svg?branch=Develop)](https://github.com/SpiritTechDevelopment/SpiritVpn-Telegram-Bot/actions/workflows/ci.yml)

Telegram-бот и mini app для продажи доступа к SpiritVPN (VLESS + REALITY).
Сервис — product-клиент бэкенда `spiritvpnd`: обращается к нему по
gRPC/mTLS, чтобы выдавать и проверять доступ клиентов. Доставка доступа на
ноды — задача `spiritvpnd`.

## Что это

- **Telegram-бот** (aiogram, long polling) — точка входа для клиента:
  `/start` (зацикленная GIF-анимация приветствия с кнопками приложения/
  поддержки/отзывов),
  `/status`, `/plans`, `/support`, `/help`, выдача бесплатного доступа по
  общему паролю.
- **Mini app** (FastAPI + статическая страница) — интерфейс клиента:
  список активных ссылок, остаток срока подписки, каталог тарифов,
  подписочная ссылка `/s/{token}`.
- **spiritvpnd** — отдельный Go-сервис, единый источник по доступу
  и нодам;

## С чего начать

- [Архитектура](ARCHITECTURE.md) — слои, модули, где что лежит.
- [Конфигурация](CONFIGURATION.md) — переменные окружения, локальный запуск.
- [API мини-аппа](API.md) — эндпоинты FastAPI-процесса.
- [Тестирование](TESTING.md) — unit- и интеграционные тесты, CI.
- [Развёртывание](DEPLOYMENT.md) — CI/CD, публикация образа, связь с
  `Infrastructure`.
- [План разработки](ROADMAP.md) — что реализовано, что нет.
- [FAQ](FAQ.md) — частые вопросы по бесплатному доступу, тест-кодам,
  ошибкам `spiritvpnd`.

## Связанные репозитории

- `SpiritVPN` — Go-бэкенд `spiritvpnd`, держатель доступа и нод.
- `Infrastructure` — desired-state окружений, PKI, приёмная сторона для
  образов сервисов.
