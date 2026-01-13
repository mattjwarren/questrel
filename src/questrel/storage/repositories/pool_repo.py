from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import (
    CharacterPoolItem,
    LocationPoolItem,
    PropPoolItem,
    ResourcePool,
)


class PoolRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_pool(self, pool_id: str) -> ResourcePool | None:
        return await self._session.get(ResourcePool, pool_id)

    async def list_pools(self, *, kind: str | None = None, active_only: bool = True) -> list[ResourcePool]:
        stmt = select(ResourcePool)
        if kind is not None:
            stmt = stmt.where(ResourcePool.kind == kind)
        if active_only:
            stmt = stmt.where(ResourcePool.is_active.is_(True))
        res = await self._session.execute(stmt)
        return list(res.scalars().all())

    async def list_character_items(self, pool_id: str, *, active_only: bool = True) -> list[CharacterPoolItem]:
        stmt = (
            select(CharacterPoolItem)
            .where(CharacterPoolItem.pool_id == pool_id)
            .options(selectinload(CharacterPoolItem.resource), selectinload(CharacterPoolItem.condition_expr))
        )
        if active_only:
            stmt = stmt.where(CharacterPoolItem.is_active.is_(True))
        res = await self._session.execute(stmt)
        return list(res.scalars().all())

    async def list_location_items(self, pool_id: str, *, active_only: bool = True) -> list[LocationPoolItem]:
        stmt = (
            select(LocationPoolItem)
            .where(LocationPoolItem.pool_id == pool_id)
            .options(selectinload(LocationPoolItem.resource), selectinload(LocationPoolItem.condition_expr))
        )
        if active_only:
            stmt = stmt.where(LocationPoolItem.is_active.is_(True))
        res = await self._session.execute(stmt)
        return list(res.scalars().all())

    async def list_prop_items(self, pool_id: str, *, active_only: bool = True) -> list[PropPoolItem]:
        stmt = (
            select(PropPoolItem)
            .where(PropPoolItem.pool_id == pool_id)
            .options(selectinload(PropPoolItem.resource), selectinload(PropPoolItem.condition_expr))
        )
        if active_only:
            stmt = stmt.where(PropPoolItem.is_active.is_(True))
        res = await self._session.execute(stmt)
        return list(res.scalars().all())
