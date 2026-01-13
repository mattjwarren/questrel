import pytest


from questrel.demos.text_adventure import build_game
from questrel.models.generated import GeneratedPlay
from questrel.models.request import GenerationRequest
from questrel.models.state import State
from questrel.api import generate_play_from_url
from questrel.seed.demo_seed import seed_demo_db


@pytest.mark.asyncio
async def test_text_adventure_builds_world(tmp_path) -> None:
    db_path = tmp_path / "demo.db"
    db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    await seed_demo_db(db_url)

    req = GenerationRequest(max_characters=3, location_count=3, prop_count=2, seed=None)
    state = State(flags={"allow": True, "brave": True, "has_key": True, "magic": True})
    play = await generate_play_from_url(db_url, req, state=state, seed=1)
    assert isinstance(play, GeneratedPlay)

    game = build_game(play=play, state=state)
    text = game.render_room()
    assert text
    assert "Exits" in text
