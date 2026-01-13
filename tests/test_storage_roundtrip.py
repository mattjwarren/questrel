import asyncio

import pytest


from questrel.storage.engine import create_engine, create_sessionmaker, session_scope
from questrel.storage.models import Base, PlayTemplate, ScriptNode
from questrel.storage.repositories.graph_repo import GraphRepository


@pytest.mark.asyncio
async def test_storage_roundtrip(tmp_path) -> None:
    db_path = tmp_path / "questrel_test.db"
    engine = create_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = create_sessionmaker(engine)
    async with session_scope(session_maker) as session:
        session.add(PlayTemplate(id="tpl", key="k", name="N", description=None))
        session.add(ScriptNode(id="n1", template_id="tpl", key="start", node_type="scene", text="hi", metadata_json={"a": 1}))

    async with session_scope(session_maker) as session:
        repo = GraphRepository(session)
        nodes = await repo.list_nodes("tpl")
        assert len(nodes) == 1
        assert nodes[0].metadata_json["a"] == 1

    await engine.dispose()
