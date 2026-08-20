from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spiritvpn_bot.application.plans import PlanCatalog, build_plan_catalog
from spiritvpn_bot.application.ports.clock import Clock
from spiritvpn_bot.application.ports.event_bus import EventPublisher
from spiritvpn_bot.application.ports.ids import IdGenerator
from spiritvpn_bot.application.ports.updates_guard import UpdatesGuard
from spiritvpn_bot.application.ports.vpn_gateway import VPNAccessGateway
from spiritvpn_bot.application.subscription_token import SubscriptionTokenSigner
from spiritvpn_bot.application.use_cases.confirm_payment import ConfirmPaymentUseCase
from spiritvpn_bot.application.use_cases.get_my_links import GetMyLinksUseCase
from spiritvpn_bot.application.use_cases.purchase_subscription import PurchaseSubscriptionUseCase
from spiritvpn_bot.application.use_cases.redeem_friend_code import RedeemFriendCodeUseCase
from spiritvpn_bot.application.use_cases.request_vpn_access import RequestAccessUseCase
from spiritvpn_bot.config import Settings, load_settings
from spiritvpn_bot.infrastructure.clock import SystemClock
from spiritvpn_bot.infrastructure.events.logging_publisher import LoggingEventPublisher
from spiritvpn_bot.infrastructure.ids import UuidIdGenerator
from spiritvpn_bot.infrastructure.postgres.engine import build_engine, build_session_factory
from spiritvpn_bot.infrastructure.postgres.unit_of_work import SqlAlchemyUnitOfWork
from spiritvpn_bot.infrastructure.postgres.updates_guard import PostgresUpdatesGuard
from spiritvpn_bot.infrastructure.spiritvpn_grpc.client import build_customer_access_stub
from spiritvpn_bot.infrastructure.spiritvpn_grpc.gateway import SpiritVPNGateway


@dataclass
class Container:
    """Реализация сборки контейнера зависимостей"""

    settings: Settings
    session_factory: async_sessionmaker[AsyncSession]
    vpn_gateway: VPNAccessGateway
    plans: PlanCatalog
    token_signer: SubscriptionTokenSigner
    clock: Clock
    id_generator: IdGenerator
    events: EventPublisher
    updates_guard: UpdatesGuard

    def _new_uow(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self.session_factory)

    def purchase_subscription_use_case(self) -> PurchaseSubscriptionUseCase:
        return PurchaseSubscriptionUseCase(self._new_uow(), self.id_generator, self.clock)

    def confirm_payment_use_case(self) -> ConfirmPaymentUseCase:
        return ConfirmPaymentUseCase(self._new_uow(), self.clock, self.events)

    def redeem_friend_code_use_case(self) -> RedeemFriendCodeUseCase:
        return RedeemFriendCodeUseCase(
            self._new_uow(),
            self.id_generator,
            self.clock,
            self.events,
            self.plans,
            self.settings.friends_shared_code,
        )

    def request_access_use_case(self) -> RequestAccessUseCase:
        return RequestAccessUseCase(self._new_uow(), self.vpn_gateway, self.events)

    def get_my_links_use_case(self) -> GetMyLinksUseCase:
        return GetMyLinksUseCase(self.vpn_gateway)


def build_container(settings: Settings | None = None) -> Container:
    """Собирает Container из настроек процесса.

    Args:
        settings: настройки; по умолчанию читаются из окружения.

    Returns:
        Готовый корень.
    """
    resolved = settings or load_settings()

    engine = build_engine(resolved.database_url)
    session_factory = build_session_factory(engine)

    stub = build_customer_access_stub(
        target=resolved.spiritvpnd_grpc_target,
        client_cert_file=resolved.spiritvpnd_tls_client_cert_file,
        client_key_file=resolved.spiritvpnd_tls_client_key_file,
        ca_file=resolved.spiritvpnd_tls_ca_file,
    )

    return Container(
        settings=resolved,
        session_factory=session_factory,
        vpn_gateway=SpiritVPNGateway(stub),
        plans=build_plan_catalog(
            friends_fleet_id=resolved.friends_plan_fleet_id,
            friends_quota_bytes=resolved.friends_plan_quota_bytes,
            friends_duration_days=resolved.friends_plan_duration_days,
        ),
        token_signer=SubscriptionTokenSigner(resolved.subscription_signing_key.encode("utf-8")),
        clock=SystemClock(),
        id_generator=UuidIdGenerator(),
        events=LoggingEventPublisher(),
        updates_guard=PostgresUpdatesGuard(session_factory),
    )
