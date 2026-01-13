from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import PlayTemplate, TemplateLocationRequirement, TemplatePropRequirement, TemplateRoleRequirement


class TemplateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_template(self, template_id: str) -> PlayTemplate | None:
        return await self._session.get(PlayTemplate, template_id)

    async def list_role_requirements(self, template_id: str) -> list[TemplateRoleRequirement]:
        res = await self._session.execute(
            select(TemplateRoleRequirement).where(TemplateRoleRequirement.template_id == template_id)
        )
        return list(res.scalars().all())

    async def list_location_requirements(self, template_id: str) -> list[TemplateLocationRequirement]:
        res = await self._session.execute(
            select(TemplateLocationRequirement).where(TemplateLocationRequirement.template_id == template_id)
        )
        return list(res.scalars().all())

    async def list_prop_requirements(self, template_id: str) -> list[TemplatePropRequirement]:
        res = await self._session.execute(
            select(TemplatePropRequirement).where(TemplatePropRequirement.template_id == template_id)
        )
        return list(res.scalars().all())
