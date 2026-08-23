from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация проекта."""

    model_config = SettingsConfigDict(env_prefix="BOT_", env_file=".env", extra="ignore")

    telegram_bot_token: str
    log_level: str = Field(default="INFO", description="уровень логирования, например INFO, DEBUG")
    database_url: str = Field(
        description="postgresql+asyncpg://... — своя база бота, не база spiritvpnd"
    )

    spiritvpnd_grpc_target: str = Field(description="host:port, например spiritvpnd.internal:8443")
    spiritvpnd_tls_client_cert_file: str
    spiritvpnd_tls_client_key_file: str
    spiritvpnd_tls_ca_file: str

    subscription_base_url: str = Field(
        description="публичный базовый URL для /s/{token}, например https://sub.spiritvpn.app"
    )

    mini_app_url: str = Field(description="публичный URL развёрнутого Telegram Mini App")
    mini_app_http_port: int = Field(
        default=8080, description="порт, на котором `python -m spiritvpn_bot api` слушает HTTP"
    )

    support_url: str = Field(
        description="ссылка на поддержку 24/7 (аккаунт или группа в Telegram) для /start и /support"
    )
    reviews_url: str = Field(
        description="ссылка на Telegram-канал с отзывами для кнопки «Отзывы» в /start"
    )

    subscription_signing_key: str = Field(
        description="секрет для подписи токена /s/{token} (SubscriptionTokenSigner)"
    )

    friends_plan_fleet_id: int = Field(description="vpn_fleet_id для бесплатного плана друзей")
    friends_plan_quota_bytes: int = Field(
        default=100 * 1024**3, description="квота трафика на ноду для бесплатного плана"
    )
    friends_plan_duration_days: int = Field(
        default=30, description="срок действия бесплатного плана в днях"
    )
    friends_shared_code: str = Field(
        description=(
            "общий пароль для бесплатного доступа — только для своих типов, "
            "никогда не упоминается в публичных ответах бота"
        )
    )

    error_notifications_chat_id: str | None = Field(
        default=None,
        validation_alias="TELEGRAM_CHAT_ID",
        description=("chat_id топика/группы для пересылки логов уровня error/exception "),
    )
    error_notifications_message_thread_id: int | None = Field(
        default=None, description="message_thread_id топика внутри группы, если это форум"
    )
    error_notifications_bot_token: str | None = Field(
        default=None,
        validation_alias="TELEGRAM_BOT_TOKEN",
        description=("Токен отдельного бота для уведомлений об ошибках "),
    )


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
