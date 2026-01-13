"""Questrel CLI.

Supports:
- Seeding a demo SQLite database.
- Generating a play/quest from a DB.

This is intended as a small developer/demo tool, not a full authoring UI.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from questrel.api import generate_play_from_url
from questrel.logging import configure_logging, get_logger
from questrel.models.request import GenerationRequest
from questrel.models.state import State
from questrel.seed.demo_seed import seed_demo_db


logger = get_logger("cli")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="questrel", description="Questrel demo CLI")
    parser.add_argument("--log-file", default="questrel.log")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--no-log", action="store_true")

    sub = parser.add_subparsers(dest="cmd", required=True)

    seed = sub.add_parser("seed", help="Seed a demo SQLite DB")
    seed.add_argument("--db", default="sqlite+aiosqlite:///./questrel_demo.db")
    seed.add_argument("--overwrite", action="store_true", help="Delete DB file first (sqlite:///./file.db only)")

    demo = sub.add_parser("demo", help="Seed then generate multiple plays")
    demo.add_argument("--db", default="sqlite+aiosqlite:///./questrel_demo.db")
    demo.add_argument("--overwrite", action="store_true", help="Delete DB file first (sqlite:///./file.db only)")
    demo.add_argument("--runs", type=int, default=5, help="Number of plays to generate")
    demo.add_argument("--start-seed", type=int, default=1, help="First seed to use")
    demo.add_argument("--json", action="store_true", help="Print full JSON per run")
    demo.add_argument(
        "--flag",
        action="append",
        default=[],
        help='State flag in the form key=value (value supports true/false/null/int/float/str)',
    )
    demo.add_argument("--flags-json", default=None, help="Path to JSON file containing flags dict")

    gen = sub.add_parser("generate", help="Generate a play/quest")
    gen.add_argument("--db", default="sqlite+aiosqlite:///./questrel_demo.db")
    gen.add_argument("--max-characters", type=int, default=3)
    gen.add_argument("--locations", type=int, default=2)
    gen.add_argument("--props", type=int, default=1)
    gen.add_argument("--template-key", default=None)
    gen.add_argument("--seed", type=int, default=0)
    gen.add_argument(
        "--flag",
        action="append",
        default=[],
        help='State flag in the form key=value (value supports true/false/null/int/float/str)',
    )
    gen.add_argument("--flags-json", default=None, help="Path to JSON file containing flags dict")

    args = parser.parse_args(argv)

    configure_logging(
        enabled=not args.no_log,
        log_file=args.log_file,
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
    )

    try:
        if args.cmd == "seed":
            asyncio.run(_cmd_seed(db_url=args.db, overwrite=bool(args.overwrite)))
            return 0

        if args.cmd == "demo":
            asyncio.run(
                _cmd_demo(
                    db_url=args.db,
                    overwrite=bool(args.overwrite),
                    runs=int(args.runs),
                    start_seed=int(args.start_seed),
                    flags_json=args.flags_json,
                    flags_kv=list(args.flag),
                    json_output=bool(args.json),
                )
            )
            return 0

        if args.cmd == "generate":
            asyncio.run(
                _cmd_generate(
                    db_url=args.db,
                    max_characters=int(args.max_characters),
                    locations=int(args.locations),
                    props=int(args.props),
                    template_key=args.template_key,
                    seed=int(args.seed),
                    flags_json=args.flags_json,
                    flags_kv=list(args.flag),
                )
            )
            return 0

        return 2
    except Exception as exc:  # noqa: BLE001
        logger.exception("CLI failed: %s", exc)
        return 1


async def _cmd_seed(*, db_url: str, overwrite: bool) -> None:
    if overwrite:
        _maybe_delete_sqlite_file(db_url)
    await seed_demo_db(db_url)


async def _cmd_demo(
    *,
    db_url: str,
    overwrite: bool,
    runs: int,
    start_seed: int,
    flags_json: str | None,
    flags_kv: list[str],
    json_output: bool,
) -> None:
    if runs <= 0:
        raise ValueError("--runs must be > 0")
    if overwrite:
        _maybe_delete_sqlite_file(db_url)

    await seed_demo_db(db_url)

    flags: dict[str, Any] = {}
    if flags_json:
        flags.update(json.loads(Path(flags_json).read_text(encoding="utf-8")))
    for kv in flags_kv:
        k, v = _parse_kv(kv)
        flags[k] = v

    state = State(flags=flags)
    req = GenerationRequest(max_characters=3, location_count=2, prop_count=1, seed=None)

    for i in range(runs):
        run_seed = start_seed + i
        generated = await generate_play_from_url(db_url, req, state=state, seed=run_seed)
        if json_output:
            print(generated.model_dump_json())
        else:
            print(
                f"run={i+1} seed={run_seed} template={generated.metadata.get('template_key')} id={generated.generated_id}"
            )


async def _cmd_generate(
    *,
    db_url: str,
    max_characters: int,
    locations: int,
    props: int,
    template_key: str | None,
    seed: int,
    flags_json: str | None,
    flags_kv: list[str],
) -> None:
    flags: dict[str, Any] = {}
    if flags_json:
        flags.update(json.loads(Path(flags_json).read_text(encoding="utf-8")))
    for kv in flags_kv:
        k, v = _parse_kv(kv)
        flags[k] = v

    request = GenerationRequest(
        max_characters=max_characters,
        location_count=locations,
        prop_count=props,
        template_key=template_key,
        seed=seed,
    )
    state = State(flags=flags)
    generated = await generate_play_from_url(db_url, request, state=state, seed=seed)
    print(generated.model_dump_json())


def _maybe_delete_sqlite_file(db_url: str) -> None:
    # Only supports sqlite file URLs in the common demo form.
    if not db_url.startswith("sqlite+"):
        raise ValueError("--overwrite only supported for sqlite+... URLs")

    if ":///./" in db_url:
        filename = db_url.split(":///./", 1)[1]
        path = Path.cwd() / filename
        if path.exists():
            path.unlink()


def _parse_kv(kv: str) -> tuple[str, Any]:
    if "=" not in kv:
        raise ValueError("--flag must be key=value")
    key, raw = kv.split("=", 1)
    key = key.strip()
    raw = raw.strip()
    if raw.lower() in {"true", "false"}:
        return key, raw.lower() == "true"
    if raw.lower() in {"null", "none"}:
        return key, None
    # Try int, then float.
    try:
        return key, int(raw)
    except ValueError:
        pass
    try:
        return key, float(raw)
    except ValueError:
        pass
    return key, raw
