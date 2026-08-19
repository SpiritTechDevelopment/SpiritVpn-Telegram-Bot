"""Гейт и фикстуры интеграционных тестов Postgres."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spiritvpn_bot.infrastructure.postgres.engine import build_engine, build_session_factory
from spiritvpn_bot.infrastructure.postgres.unit_of_work import SqlAlchemyUnitOfWork

_TRUNCATED_TABLES = ("orders", "customer_command_sequences")


def _database_url() -> str | None:
    if not os.environ.get("BOT_INTEGRATION_TESTS"):
        return None
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("BOT_INTEGRATION_TESTS задан, а DATABASE_URL пуст")
    return url


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    url = _database_url()
    if url is None:
        pytest.skip("BOT_INTEGRATION_TESTS не задан")

    engine = build_engine(url)
    async with engine.begin() as conn:
        for table in _TRUNCATED_TABLES:
            await conn.execute(text(f"TRUNCATE {table} CASCADE"))
    try:
        yield build_session_factory(engine)
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
def uow(session_factory: async_sessionmaker[AsyncSession]) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(session_factory)
