"""Minimal seed data insertion.

This is used for Phase B sanity checks. Phase C will add richer seeding.
"""

from __future__ import annotations

import asyncio

from questrel.storage.engine import create_engine, create_sessionmaker, session_scope
from questrel.storage.models import (
    Base,
    CharacterPoolItem,
    CharacterResource,
    ConditionExpression,
    LocationPoolItem,
    LocationResource,
    PlayTemplate,
    PropPoolItem,
    PropResource,
    ResourcePool,
    ScriptEdge,
    ScriptNode,
    TemplateLocationRequirement,
    TemplatePropRequirement,
    TemplateRoleRequirement,
)


async def main() -> None:
    engine = create_engine("sqlite+aiosqlite:///./questrel.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = create_sessionmaker(engine)
    async with session_scope(session_maker) as session:
        tpl = PlayTemplate(id="tpl_1", key="demo", name="Demo Template", description="Seeded template")
        session.add(tpl)

        session.add_all(
            [
                TemplateRoleRequirement(
                    id="rr_1",
                    template_id=tpl.id,
                    role_type="hero",
                    count_min=1,
                    count_max=1,
                    order_index=0,
                ),
                TemplateRoleRequirement(
                    id="rr_2",
                    template_id=tpl.id,
                    role_type="villain",
                    count_min=1,
                    count_max=1,
                    order_index=1,
                ),
                TemplateLocationRequirement(
                    id="lr_1",
                    template_id=tpl.id,
                    count_min=1,
                    count_max=4,
                    order_index=0,
                ),
                TemplatePropRequirement(
                    id="pr_1",
                    template_id=tpl.id,
                    count_min=0,
                    count_max=3,
                    order_index=0,
                ),
            ]
        )

        # Nodes
        n1 = ScriptNode(id="n_start", template_id=tpl.id, key="start", node_type="scene", text="A meeting.")
        n2 = ScriptNode(id="n_end", template_id=tpl.id, key="end", node_type="narration", text="The end.")
        session.add_all([n1, n2])

        # Condition: a flag gate
        c1 = ConditionExpression(id="c1", template_id=tpl.id, expr_text='state.flags["allow_end"] == True')
        session.add(c1)

        # Edges
        session.add(
            ScriptEdge(
                id="e1",
                template_id=tpl.id,
                from_node_id=n1.id,
                to_node_id=n2.id,
                when_expr_id=c1.id,
                priority=1,
                order_index=0,
                selection_mode="single",
            )
        )

        # Catalog
        hero = CharacterResource(id="char_hero", slug="hero", display_name="The Hero")
        villain = CharacterResource(id="char_villain", slug="villain", display_name="The Villain")
        inn = LocationResource(id="loc_inn", slug="inn", display_name="The Inn")
        forest = LocationResource(id="loc_forest", slug="forest", display_name="The Forest")
        sword = PropResource(id="prop_sword", slug="sword", display_name="A Sword")
        session.add_all([hero, villain, inn, forest, sword])

        # Pools
        p_char = ResourcePool(id="pool_char", template_id=tpl.id, key="characters", kind="character")
        p_loc = ResourcePool(id="pool_loc", template_id=tpl.id, key="locations", kind="location")
        p_prop = ResourcePool(id="pool_prop", template_id=tpl.id, key="props", kind="prop")
        session.add_all([p_char, p_loc, p_prop])

        session.add_all(
            [
                CharacterPoolItem(id="cpi1", pool_id=p_char.id, resource_id=hero.id, weight=10.0),
                CharacterPoolItem(id="cpi2", pool_id=p_char.id, resource_id=villain.id, weight=10.0),
                LocationPoolItem(id="lpi1", pool_id=p_loc.id, resource_id=inn.id, weight=10.0),
                LocationPoolItem(id="lpi2", pool_id=p_loc.id, resource_id=forest.id, weight=10.0),
                PropPoolItem(id="ppi1", pool_id=p_prop.id, resource_id=sword.id, weight=10.0),
            ]
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
