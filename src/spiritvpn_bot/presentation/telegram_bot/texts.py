"""Тексты и подписи кнопок бота — единое место для правок копирайтинга.

Хендлеры (`handlers/start.py`) импортируют константы и шаблоны отсюда вместо
того, чтобы держать строки прямо в коде — так копирайтинг можно
редактировать, не читая логику.
"""

from __future__ import annotations

WELCOME_CAPTION = (
    "🌀 SpiritVPN — ваш приватный доступ в интернет.\n"
    "🚀 Высокая скорость — выделенные серверы\n"
    "🌍 Несколько стран на выбор\n"
    "📶 Безлимитный трафик\n"
    "📱 Любое устройство — iOS, Android, Windows, macOS, Linux\n"
    "💳 От 100 ₽/мес\n\n"
    "Откройте приложение и получите доступ без границ за секунды ⚡"
)

WELCOME_FALLBACK_TEMPLATE = (
    "{caption}\n\nПриложение: {mini_app_url}\nПоддержка: {support_url}\nОтзывы: {reviews_url}"
)

FALLBACK_TEXT = (
    "Не могу распознать это сообщение. Нажмите «Открыть приложение» ниже."
    "👥 Связаться с поддержкой: /support."
)

HELP_TEXT = (
    "Команды SpiritVPN:\n\n"
    "🚀 /start — Старт бота\n"
    "📊 /status — Статус подписки и серверов\n"
    "💳 /plans — Тарифы, регионы и статус подписки\n"
    "👥 /support — Связаться с поддержкой\n"
    "⭐ /reviews — Отзывы о SpiritVPN\n"
    "❓ /help — Справка по командам\n"
)

BTN_OPEN_APP = "🚀 Открыть приложение"
BTN_OPEN_APP_DEV = "🚀 Открыть приложение (dev, в браузере)"
BTN_SUPPORT = "👥 Поддержка 24/7"
BTN_REVIEWS = "⭐ Отзывы"
BTN_SUPPORT_DIRECT = "👥 Написать в поддержку"
BTN_REVIEWS_DIRECT = "⭐ Оставить отзыв"

STATUS_NO_SUBSCRIPTION = "🔒 Подписка не активна. Откройте приложение, чтобы выбрать тариф."
STATUS_SERVERS_READY_TEMPLATE = "Серверы: {ready}/{total} активны"
STATUS_SERVERS_NONE = "Серверы ещё не выданы"
STATUS_ACTIVE_TEMPLATE = "✅ Подписка активна: осталось {days} {days_word}.\n{servers_line}"
STATUS_EXPIRED_TEMPLATE = "⏳ Подписка истекла.\n{servers_line}\n\nПродлите её в приложении."

PLANS_HEADER = "💳 Тарифы SpiritVPN"
PLANS_STATUS_ACTIVE_TEMPLATE = "✅ Активна: осталось {days} {days_word}"
PLANS_STATUS_NONE = "🔒 Подписки пока нет — выберите тариф ниже"
PLANS_STATUS_EXPIRED = "⏳ Подписка истекла — выберите тариф, чтобы продлить"
PLANS_LINE_TEMPLATE = "• {title} — {quota} · {price} ₽"
PLANS_REGIONS_HEADER = "🌍 Регионы"
# TODO: захардкожено — у spiritvpnd нет RPC вида "список доступных регионов"
# (VPNAccessGateway отдаёт только apply_access/get_links, и get_links не
# помогает: у клиента без подписки ссылок ещё нет). Как только Павел добавит
# такой метод на стороне spiritvpnd, заменить эту строку на реальный запрос.
# PLANS_REGIONS_LIST = "🇳🇱 Нидерланды · 🇩🇪 Германия · 🇱🇻 Латвия · 🇷🇴 Румыния · 🇷🇺 Россия"
PLANS_REGIONS_LIST = "🇷🇴 Румыния · 🇷🇺 Россия"
PLANS_FOOTER = "Оформить или продлить подписку на SpiritVPN можно в приложении."

SUPPORT_HEADER = "👥 Поддержка на связи 24/7:"
REVIEWS_HEADER = "⭐ Отзывы о SpiritVPN"

TEXT_EXPIRY_REGRESSION = (
    "У вас уже есть доступ на более долгий срок, чем даёт этот код. SpiritVPN "
    "не укорачивает подписку — возьмите код с бо́льшим сроком или дождитесь "
    "окончания текущего периода. Остались вопросы? Напишите в /support."
)

TEXT_ACCESS_REQUEST_FAILED = (
    "Доступ оформлен, но подключиться к серверам пока не получилось. "
    "Откройте приложение через пару минут — там будет ссылка на подписку. "
    "👥 Поддержка: /support."
)

TEXT_ACCESS_GRANTED_TEMPLATE = (
    "Готово! Подключаем ваш доступ.\n\n"
    "Ссылка подписки:\n{subscription_url}\n\n"
    "Спасибо, что выбрали SpiritVPN ❤️"
    "Будем рады вашим отзывам: /reviews\n"
)


def days_word(n: int) -> str:
    """Склонение слова «день» под число n (1 день, 2 дня, 5 дней...)."""
    if n % 10 == 1 and n % 100 != 11:
        return "день"
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return "дня"
    return "дней"
