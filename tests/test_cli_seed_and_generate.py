import json

import pytest


from questrel.models.request import GenerationRequest
from questrel.models.state import State
from questrel.seed.demo_seed import seed_demo_db
from questrel.api import generate_play_from_url


@pytest.mark.asyncio
async def test_demo_seed_produces_variety(tmp_path) -> None:
    db_path = tmp_path / "demo.db"
    db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    await seed_demo_db(db_url)

    req = GenerationRequest(max_characters=3, location_count=2, prop_count=1, seed=None)
    state = State(flags={"allow": True, "brave": True, "has_key": True, "magic": True})

    generated = [
        await generate_play_from_url(db_url, req, state=state, seed=s)
        for s in range(1, 9)
    ]

    keys = {g.metadata["template_key"] for g in generated}
    assert keys.issubset({"rescue", "heist", "mystery"})
    assert len(keys) >= 2

    # JSON output should be valid.
    json.loads(generated[0].model_dump_json())
