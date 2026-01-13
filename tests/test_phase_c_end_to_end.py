import pytest


from questrel.api import generate_play
from questrel.models.request import GenerationRequest
from questrel.models.state import State
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


@pytest.mark.asyncio
async def test_generate_play_end_to_end(tmp_path) -> None:
    db_path = tmp_path / "q.db"
    engine = create_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = create_sessionmaker(engine)
    async with session_scope(session_maker) as session:
        tpl = PlayTemplate(id="tpl", key="demo", name="Demo", description=None)
        session.add(tpl)
        session.add_all(
            [
                TemplateRoleRequirement(id="rr1", template_id=tpl.id, role_type="hero", count_min=1, count_max=1),
                TemplateRoleRequirement(id="rr2", template_id=tpl.id, role_type="villain", count_min=1, count_max=1),
                TemplateLocationRequirement(id="lr", template_id=tpl.id, count_min=1, count_max=4),
                TemplatePropRequirement(id="pr", template_id=tpl.id, count_min=0, count_max=2),
            ]
        )
        n1 = ScriptNode(id="n1", template_id=tpl.id, key="start", node_type="scene", text="start")
        n2 = ScriptNode(id="n2", template_id=tpl.id, key="end", node_type="narration", text="end")
        session.add_all([n1, n2])
        cond = ConditionExpression(id="c1", template_id=tpl.id, expr_text='state.flags["allow"] == True')
        session.add(cond)
        session.add(
            ScriptEdge(
                id="e1",
                template_id=tpl.id,
                from_node_id=n1.id,
                to_node_id=n2.id,
                when_expr_id=cond.id,
                priority=1,
                order_index=0,
                selection_mode="single",
            )
        )

        hero = CharacterResource(id="ch1", slug="hero", display_name="Hero")
        vill = CharacterResource(id="ch2", slug="vill", display_name="Villain")
        loc = LocationResource(id="l1", slug="inn", display_name="Inn")
        prop = PropResource(id="p1", slug="sword", display_name="Sword")
        session.add_all([hero, vill, loc, prop])
        pool_char = ResourcePool(id="pc", template_id=tpl.id, key="characters", kind="character")
        pool_loc = ResourcePool(id="pl", template_id=tpl.id, key="locations", kind="location")
        pool_prop = ResourcePool(id="pp", template_id=tpl.id, key="props", kind="prop")
        session.add_all([pool_char, pool_loc, pool_prop])
        session.add_all(
            [
                CharacterPoolItem(id="cpi1", pool_id=pool_char.id, resource_id=hero.id, weight=10.0),
                CharacterPoolItem(id="cpi2", pool_id=pool_char.id, resource_id=vill.id, weight=10.0),
                LocationPoolItem(id="lpi1", pool_id=pool_loc.id, resource_id=loc.id, weight=10.0),
                PropPoolItem(id="ppi1", pool_id=pool_prop.id, resource_id=prop.id, weight=10.0),
            ]
        )

    async with session_scope(session_maker) as session:
        req = GenerationRequest(max_characters=3, location_count=1, prop_count=1, template_key="demo", seed=123)
        state = State(flags={"allow": True})
        gen = await generate_play(session, req, state=state)

        assert gen.template_id == "tpl"
        assert len(gen.characters) == 2
        assert len(gen.locations) == 1
        assert len(gen.props) == 1
        assert len(gen.nodes) == 2
        assert len(gen.edges) == 1

        # JSON rendering should work.
        payload = gen.model_dump()
        assert payload["template_id"] == "tpl"

    await engine.dispose()
