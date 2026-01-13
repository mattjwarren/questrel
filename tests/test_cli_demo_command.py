import pytest


from questrel.cli import _cmd_demo


@pytest.mark.asyncio
async def test_cmd_demo_runs(tmp_path) -> None:
    db_path = tmp_path / "demo.db"
    db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    await _cmd_demo(
        db_url=db_url,
        overwrite=False,
        runs=3,
        start_seed=1,
        flags_json=None,
        flags_kv=["allow=true", "brave=true", "has_key=true", "magic=true"],
        json_output=False,
    )
