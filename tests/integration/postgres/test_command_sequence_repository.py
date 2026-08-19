from __future__ import annotations

from spiritvpn_bot.infrastructure.postgres.unit_of_work import SqlAlchemyUnitOfWork


async def test_unknown_customer_has_no_last_issued(uow: SqlAlchemyUnitOfWork) -> None:
    async with uow as tx:
        last = await tx.command_sequence.last_issued_for_update("tg:1")
        await tx.commit()
    assert last is None


async def test_record_then_read_back(uow: SqlAlchemyUnitOfWork) -> None:
    async with uow as tx:
        await tx.command_sequence.record("tg:1", 1)
        await tx.commit()

    async with uow as tx:
        last = await tx.command_sequence.last_issued_for_update("tg:1")
        await tx.commit()

    assert last == 1


async def test_record_upserts_rather_than_duplicating(uow: SqlAlchemyUnitOfWork) -> None:
    async with uow as tx:
        await tx.command_sequence.record("tg:1", 1)
        await tx.commit()

    async with uow as tx:
        await tx.command_sequence.record("tg:1", 2)
        await tx.commit()

    async with uow as tx:
        last = await tx.command_sequence.last_issued_for_update("tg:1")
        await tx.commit()

    assert last == 2


async def test_different_customers_are_independent(uow: SqlAlchemyUnitOfWork) -> None:
    async with uow as tx:
        await tx.command_sequence.record("tg:alice", 5)
        await tx.command_sequence.record("tg:bob", 1)
        await tx.commit()

    async with uow as tx:
        alice = await tx.command_sequence.last_issued_for_update("tg:alice")
        bob = await tx.command_sequence.last_issued_for_update("tg:bob")
        await tx.commit()

    assert alice == 5
    assert bob == 1
