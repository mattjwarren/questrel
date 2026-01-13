from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import ScriptEdge, ScriptNode


class GraphRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_nodes(self, template_id: str) -> list[ScriptNode]:
        res = await self._session.execute(select(ScriptNode).where(ScriptNode.template_id == template_id))
        return list(res.scalars().all())

    async def list_edges(self, template_id: str) -> list[ScriptEdge]:
        res = await self._session.execute(
            select(ScriptEdge)
            .where(ScriptEdge.template_id == template_id)
            .options(selectinload(ScriptEdge.when_expr))
        )
        return list(res.scalars().all())
