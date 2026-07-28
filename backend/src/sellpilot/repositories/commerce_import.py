from collections.abc import Iterable
from typing import TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class CommerceImportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def id_map(self, model: type[ModelT]) -> dict[str, UUID]:
        rows = await self.session.execute(select(model.external_id, model.id))
        return {external_id: record_id for external_id, record_id in rows}

    def add_all(self, records: Iterable[Base]) -> None:
        self.session.add_all(list(records))

    async def flush(self) -> None:
        await self.session.flush()
