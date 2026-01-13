from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ConditionExpression


class ConditionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, condition_id: str) -> ConditionExpression | None:
        return await self._session.get(ConditionExpression, condition_id)

    async def upsert_by_text(
        self,
        *,
        condition_id: str,
        template_id: str,
        expr_text: str,
        language: str = "questrel_expr",
        version_int: int = 1,
    ) -> ConditionExpression:
        # Basic dedupe by checksum+template+version+language.
        checksum = hashlib.sha256(expr_text.encode("utf-8")).hexdigest()
        res = await self._session.execute(
            select(ConditionExpression).where(
                ConditionExpression.template_id == template_id,
                ConditionExpression.language == language,
                ConditionExpression.version_int == version_int,
                ConditionExpression.expr_text == expr_text,
            )
        )
        existing = res.scalars().first()
        if existing is not None:
            return existing

        created = ConditionExpression(
            id=condition_id,
            template_id=template_id,
            language=language,
            version_int=version_int,
            expr_text=expr_text,
        )
        self._session.add(created)
        return created
