"""Demo seed dataset.

This is used by the CLI demo to populate a SQLite database with enough variety
to see different generated plays.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from questrel.logging import get_logger
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


logger = get_logger("seed")


async def seed_demo_db(db_url: str) -> None:
    engine = create_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = create_sessionmaker(engine)
    async with session_scope(session_maker) as session:
        # If the demo content already exists, don't insert duplicates.
        existing = await session.execute(select(PlayTemplate.id).limit(1))
        if existing.first() is not None:
            logger.info("Demo DB already seeded; skipping")
        else:
            await _insert_demo(session)

    await engine.dispose()


async def _insert_demo(session: AsyncSession) -> None:
    # Global resources
    characters = [
        CharacterResource(id="c_hero", slug="hero", display_name="The Hero", base_weight=5.0),
        CharacterResource(id="c_villain", slug="villain", display_name="The Villain", base_weight=5.0),
        CharacterResource(id="c_merchant", slug="merchant", display_name="A Merchant", base_weight=3.0),
        CharacterResource(id="c_guard", slug="guard", display_name="A Guard", base_weight=3.0),
        CharacterResource(id="c_mage", slug="mage", display_name="A Mage", base_weight=2.0),
    ]
    locations = [
        LocationResource(id="l_inn", slug="inn", display_name="The Inn", base_weight=5.0),
        LocationResource(id="l_market", slug="market", display_name="The Market", base_weight=4.0),
        LocationResource(id="l_forest", slug="forest", display_name="The Forest", base_weight=4.0),
        LocationResource(id="l_ruins", slug="ruins", display_name="Ancient Ruins", base_weight=2.0),
    ]
    props = [
        PropResource(id="p_sword", slug="sword", display_name="A Sword", base_weight=4.0),
        PropResource(id="p_scroll", slug="scroll", display_name="A Scroll", base_weight=2.0),
        PropResource(id="p_key", slug="key", display_name="A Key", base_weight=3.0),
        PropResource(id="p_gem", slug="gem", display_name="A Gemstone", base_weight=1.0),
    ]

    session.add_all(characters + locations + props)

    # Templates
    tpl_rescue = PlayTemplate(id="tpl_rescue", key="rescue", name="Rescue at Dusk", description="A quick rescue.")
    tpl_heist = PlayTemplate(id="tpl_heist", key="heist", name="Market Heist", description="A daring theft.")
    tpl_mystery = PlayTemplate(id="tpl_mystery", key="mystery", name="Ruins Mystery", description="A strange discovery.")
    session.add_all([tpl_rescue, tpl_heist, tpl_mystery])

    # Requirements (keep them satisfiable for small requests)
    session.add_all(
        [
            TemplateRoleRequirement(id="rr_r1", template_id=tpl_rescue.id, role_type="hero", count_min=1, count_max=1, order_index=0),
            TemplateRoleRequirement(
                id="rr_r2", template_id=tpl_rescue.id, role_type="target", count_min=1, count_max=1, order_index=1
            ),
            TemplateLocationRequirement(id="lr_r", template_id=tpl_rescue.id, count_min=1, count_max=3, order_index=0),
            TemplatePropRequirement(id="pr_r", template_id=tpl_rescue.id, count_min=0, count_max=2, order_index=0),
        ]
    )
    session.add_all(
        [
            TemplateRoleRequirement(id="rr_h1", template_id=tpl_heist.id, role_type="thief", count_min=1, count_max=1, order_index=0),
            TemplateRoleRequirement(
                id="rr_h2", template_id=tpl_heist.id, role_type="guard", count_min=1, count_max=1, order_index=1
            ),
            TemplateLocationRequirement(id="lr_h", template_id=tpl_heist.id, count_min=1, count_max=2, order_index=0),
            TemplatePropRequirement(id="pr_h", template_id=tpl_heist.id, count_min=1, count_max=2, order_index=0),
        ]
    )
    session.add_all(
        [
            TemplateRoleRequirement(id="rr_m1", template_id=tpl_mystery.id, role_type="explorer", count_min=1, count_max=1, order_index=0),
            TemplateRoleRequirement(
                id="rr_m2", template_id=tpl_mystery.id, role_type="witness", count_min=1, count_max=1, order_index=1
            ),
            TemplateLocationRequirement(id="lr_m", template_id=tpl_mystery.id, count_min=2, count_max=4, order_index=0),
            TemplatePropRequirement(id="pr_m", template_id=tpl_mystery.id, count_min=0, count_max=2, order_index=0),
        ]
    )

    # Conditions (edge gating)
    c_allow = ConditionExpression(id="cond_allow", template_id=tpl_rescue.id, expr_text='state.flags["allow"] == True')
    c_brave = ConditionExpression(id="cond_brave", template_id=tpl_rescue.id, expr_text='state.flags["brave"] == True')
    c_has_key = ConditionExpression(id="cond_has_key", template_id=tpl_heist.id, expr_text='state.flags["has_key"] == True')
    c_magic = ConditionExpression(id="cond_magic", template_id=tpl_mystery.id, expr_text='state.flags["magic"] == True')
    session.add_all([c_allow, c_brave, c_has_key, c_magic])

    # Graphs
    await _insert_graph_rescue(session, tpl_rescue.id, c_allow.id, c_brave.id)
    await _insert_graph_heist(session, tpl_heist.id, c_has_key.id)
    await _insert_graph_mystery(session, tpl_mystery.id, c_magic.id)

    # Pools (template-specific)
    await _insert_pools(session, tpl_rescue.id)
    await _insert_pools(session, tpl_heist.id)
    await _insert_pools(session, tpl_mystery.id)


async def _insert_graph_rescue(session: AsyncSession, template_id: str, allow_id: str, brave_id: str) -> None:
    n_start = ScriptNode(id=f"{template_id}_start", template_id=template_id, key="start", node_type="scene", text="A cry for help.")
    n_sneak = ScriptNode(id=f"{template_id}_sneak", template_id=template_id, key="sneak", node_type="narration", text="You sneak in.")
    n_fight = ScriptNode(id=f"{template_id}_fight", template_id=template_id, key="fight", node_type="narration", text="You charge in.")
    n_end = ScriptNode(id=f"{template_id}_end", template_id=template_id, key="end", node_type="narration", text="Rescue complete.")
    session.add_all([n_start, n_sneak, n_fight, n_end])

    # MULTI event edges at top priority: can emit side events + choose a path.
    session.add_all(
        [
            ScriptEdge(
                id=f"{template_id}_e_allow",
                template_id=template_id,
                from_node_id=n_start.id,
                to_node_id=n_sneak.id,
                when_expr_id=allow_id,
                priority=2,
                order_index=0,
                selection_mode="single",
                weight=1.0,
            ),
            ScriptEdge(
                id=f"{template_id}_e_brave",
                template_id=template_id,
                from_node_id=n_start.id,
                to_node_id=n_fight.id,
                when_expr_id=brave_id,
                priority=2,
                order_index=1,
                selection_mode="single",
                weight=2.0,
            ),
            ScriptEdge(
                id=f"{template_id}_e_end_sneak",
                template_id=template_id,
                from_node_id=n_sneak.id,
                to_node_id=n_end.id,
                when_expr_id=None,
                priority=1,
                order_index=0,
                selection_mode="single",
            ),
            ScriptEdge(
                id=f"{template_id}_e_end_fight",
                template_id=template_id,
                from_node_id=n_fight.id,
                to_node_id=n_end.id,
                when_expr_id=None,
                priority=1,
                order_index=0,
                selection_mode="single",
            ),
        ]
    )


async def _insert_graph_heist(session: AsyncSession, template_id: str, has_key_id: str) -> None:
    n_start = ScriptNode(id=f"{template_id}_start", template_id=template_id, key="start", node_type="scene", text="A plan forms.")
    n_inside = ScriptNode(id=f"{template_id}_inside", template_id=template_id, key="inside", node_type="scene", text="Inside the stall.")
    n_escape = ScriptNode(id=f"{template_id}_escape", template_id=template_id, key="escape", node_type="narration", text="You escape.")
    session.add_all([n_start, n_inside, n_escape])

    session.add_all(
        [
            ScriptEdge(
                id=f"{template_id}_e_key",
                template_id=template_id,
                from_node_id=n_start.id,
                to_node_id=n_inside.id,
                when_expr_id=has_key_id,
                priority=2,
                order_index=0,
                selection_mode="single",
                weight=3.0,
            ),
            ScriptEdge(
                id=f"{template_id}_e_force",
                template_id=template_id,
                from_node_id=n_start.id,
                to_node_id=n_inside.id,
                when_expr_id=None,
                priority=1,
                order_index=0,
                selection_mode="single",
                weight=1.0,
            ),
            ScriptEdge(
                id=f"{template_id}_e_escape",
                template_id=template_id,
                from_node_id=n_inside.id,
                to_node_id=n_escape.id,
                when_expr_id=None,
                priority=1,
                order_index=0,
                selection_mode="single",
            ),
        ]
    )


async def _insert_graph_mystery(session: AsyncSession, template_id: str, magic_id: str) -> None:
    n_start = ScriptNode(id=f"{template_id}_start", template_id=template_id, key="start", node_type="scene", text="A strange sign.")
    n_ruins = ScriptNode(id=f"{template_id}_ruins", template_id=template_id, key="ruins", node_type="scene", text="In the ruins.")
    n_reveal = ScriptNode(id=f"{template_id}_reveal", template_id=template_id, key="reveal", node_type="narration", text="A revelation.")
    n_end = ScriptNode(id=f"{template_id}_end", template_id=template_id, key="end", node_type="narration", text="Mystery solved.")
    session.add_all([n_start, n_ruins, n_reveal, n_end])

    session.add_all(
        [
            ScriptEdge(
                id=f"{template_id}_e_go",
                template_id=template_id,
                from_node_id=n_start.id,
                to_node_id=n_ruins.id,
                when_expr_id=None,
                priority=1,
                order_index=0,
                selection_mode="single",
            ),
            ScriptEdge(
                id=f"{template_id}_e_magic",
                template_id=template_id,
                from_node_id=n_ruins.id,
                to_node_id=n_reveal.id,
                when_expr_id=magic_id,
                priority=2,
                order_index=0,
                selection_mode="single",
                weight=2.0,
            ),
            ScriptEdge(
                id=f"{template_id}_e_normal",
                template_id=template_id,
                from_node_id=n_ruins.id,
                to_node_id=n_end.id,
                when_expr_id=None,
                priority=1,
                order_index=1,
                selection_mode="single",
                weight=1.0,
            ),
            ScriptEdge(
                id=f"{template_id}_e_end",
                template_id=template_id,
                from_node_id=n_reveal.id,
                to_node_id=n_end.id,
                when_expr_id=None,
                priority=1,
                order_index=0,
                selection_mode="single",
            ),
        ]
    )


async def _insert_pools(session: AsyncSession, template_id: str) -> None:
    p_char = ResourcePool(id=f"{template_id}_pool_char", template_id=template_id, key="characters", kind="character")
    p_loc = ResourcePool(id=f"{template_id}_pool_loc", template_id=template_id, key="locations", kind="location")
    p_prop = ResourcePool(id=f"{template_id}_pool_prop", template_id=template_id, key="props", kind="prop")
    session.add_all([p_char, p_loc, p_prop])

    # Character mixes differ per template by weights.
    char_weights = {
        "tpl_rescue": {"c_hero": 10.0, "c_guard": 3.0, "c_merchant": 2.0, "c_villain": 6.0},
        "tpl_heist": {"c_merchant": 6.0, "c_guard": 8.0, "c_villain": 4.0, "c_hero": 2.0},
        "tpl_mystery": {"c_mage": 8.0, "c_hero": 3.0, "c_merchant": 2.0, "c_villain": 2.0},
    }
    for cid, w in char_weights.get(template_id, {}).items():
        session.add(CharacterPoolItem(id=f"{template_id}_cpi_{cid}", pool_id=p_char.id, resource_id=cid, weight=w))

    # Locations
    loc_weights = {
        "tpl_rescue": {"l_inn": 7.0, "l_forest": 5.0, "l_market": 3.0},
        "tpl_heist": {"l_market": 10.0, "l_inn": 5.0},
        "tpl_mystery": {"l_ruins": 10.0, "l_forest": 5.0, "l_inn": 2.0},
    }
    for lid, w in loc_weights.get(template_id, {}).items():
        session.add(LocationPoolItem(id=f"{template_id}_lpi_{lid}", pool_id=p_loc.id, resource_id=lid, weight=w))

    # Props
    prop_weights = {
        "tpl_rescue": {"p_sword": 5.0, "p_key": 3.0},
        "tpl_heist": {"p_key": 10.0, "p_gem": 6.0},
        "tpl_mystery": {"p_scroll": 10.0, "p_gem": 4.0},
    }
    for pid, w in prop_weights.get(template_id, {}).items():
        session.add(PropPoolItem(id=f"{template_id}_ppi_{pid}", pool_id=p_prop.id, resource_id=pid, weight=w))
