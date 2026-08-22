# Развёртывание

## Git-флоу и релизы

Основная ветка — `Develop`. Изменения вносятся через отдельную ветку и
pull request в `Develop`; прямые пуши в `Develop` допустимы только до
прод-этапа.

## CI/CD (`.github/workflows/ci.yml`)

На каждый push и pull request запускаются `test` и `lint` — подробности в
[Тестировании](TESTING.md). Дальше, только на push непосредственно в
`Develop` и только после успешных `test`+`lint`, job `images`:

1. **Собирает и публикует образ** в
   `ghcr.io/spirittechdevelopment/spiritvpn-bot` с тегом `sha-<commit>`.
   Плавающего тега (`latest`, `develop`) нет: идентичность образа для
   деплоя — digest, а не тег.
2. **Smoke-тестирует опубликованный образ** прямо в CI, двумя точками
   входа: `alembic --version` через `--entrypoint alembic` и запуск самого
   бота без аргументов (ожидается код выхода `2` — «интерпретатор и пакет
   на месте», доступ к переменным окружения для этого не нужен). Проверка
   появилась после инцидента: сборка была зелёной и тогда, когда `alembic`
   в собранном образе фактически не запускался (Poetry прописывает
   консольным скриптам абсолютный шебанг на интерпретатор своего venv, а
   сборка в одном каталоге с копированием в другой оставляла шебанг
   указывать в никуда) — обнаружилось это не в CI, а на управляющем хосте
   посреди выкатки.
3. **Отправляет `repository_dispatch` в `Infrastructure`** —
   `event_type: bot-release` с `environment`, `source_git_sha` и
   `image: {repository, digest}` (не тег — digest, он не переставляется,
   и только он делает выкатку воспроизводимой). Это уведомление о факте
   публикации, а не команда на выкатку: что из него следует, решает
   `Infrastructure` — она закрепляет digest коммитом в desired state, и
   уже появление этого коммита в её `main` запускает `control-deploy`.

Продвижение образа в прод (по тегу `v*`, как у `SpiritVPN`) не реализовано —
целевого prod-окружения для бота пока нет.

## Приёмная сторона в `Infrastructure`

Репозиторий публикует образ и уведомляет об этом — дальше решает
`Infrastructure`. Для бота там пока нет полностью настроенной принимающей
стороны:

- mTLS-идентичность зарезервирована: `spiffe://spiritvpn/develop/service/customer-service`
  указана в `desired/environments/develop/environment.yml`
  (`customer_access_writers`/`customer_access_readers`); профиль сертификата
  `customer-service` есть в `fleetctl/pki/model.py`.
- Профиль `customer-service` в `fleetctl` зарезервирован, но пока никем не
  выпускался под конкретное окружение — это первый шаг, без которого
  остальная выкатка (Ansible-роль, `environment.yml`) не имеет смысла
  проверять.

### mTLS до `spiritvpnd`

Бот — клиент, не эмитент сертификатов: он только читает готовые PEM-файлы
с диска (`infrastructure/spiritvpn_grpc/client.py`), сам ничего не выпускает
и не запрашивает. Пока никто не выпустил и не доставил эти файлы,
подключение к `spiritvpnd` падает на TLS-хендшейке — это ожидаемо и не
связано с кодом бота. Для развёрнутого (не локального) `spiritvpnd`
`Infrastructure` должна положить в окружение бота:

| Переменная | Содержимое |
|---|---|
| `BOT_SPIRITVPND_GRPC_TARGET` | `host:port` того `spiritvpnd`, к которому подключается бот |
| `BOT_SPIRITVPND_TLS_CLIENT_CERT_FILE` | клиентский сертификат identity `spiffe://spiritvpn/develop/service/customer-service`, выпущенный `fleetctl` по профилю `customer-service` |
| `BOT_SPIRITVPND_TLS_CLIENT_KEY_FILE` | приватный ключ этого сертификата |
| `BOT_SPIRITVPND_TLS_CA_FILE` | CA, которым подписан серверный сертификат самого `spiritvpnd` (это не обязательно тот же CA, что подписывает identity бота) |

### Уведомления об ошибках

`TELEGRAM_CHAT_ID` и `TELEGRAM_BOT_TOKEN` для пересылки логов
`error`/`exception` в общий топик ошибок — те же переменные (буквально те
же имена и те же значения), что уже разданы `SpiritVPN` и `Infrastructure`.
Подробности и жёсткое ограничение «никогда не использовать основной бот
для этого» — в [Конфигурации](CONFIGURATION.md#error).
