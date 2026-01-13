from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CharacterResource, LocationResource, PropResource


class CatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_characters(self, *, active_only: bool = True) -> list[CharacterResource]:
        stmt = select(CharacterResource)
        if active_only:
            stmt = stmt.where(CharacterResource.is_active.is_(True))
        res = await self._session.execute(stmt)
        return list(res.scalars().all())

    async def list_locations(self, *, active_only: bool = True) -> list[LocationResource]:
        stmt = select(LocationResource)
        if active_only:
            stmt = stmt.where(LocationResource.is_active.is_(True))
        res = await self._session.execute(stmt)
        return list(res.scalars().all())

    async def list_props(self, *, active_only: bool = True) -> list[PropResource]:
        stmt = select(PropResource)
        if active_only:
            stmt = stmt.where(PropResource.is_active.is_(True))
        res = await self._session.execute(stmt)
        return list(res.scalars().all())
