from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация проекта."""

    model_config = SettingsConfigDict(env_prefix="BOT_", env_file=".env", extra="ignore")

    telegram_bot_token: str
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


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
