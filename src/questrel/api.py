"""Public API for Questrel generation (Phase C)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from .generator.generate import generate_play as _generate_play
from .logging import get_logger
from .models.request import GenerationRequest
from .models.state import State
from .storage.engine import create_engine, create_sessionmaker, session_scope


logger = get_logger("api")


async def generate_play(
    session: AsyncSession,
    request: GenerationRequest,
    *,
    state: State | None = None,
    seed: int | None = None,
):
    """Generate a play using an existing async SQLAlchemy session."""

    effective_seed = seed if seed is not None else (request.seed if request.seed is not None else 0)
    effective_state = state if state is not None else State(flags={})
    return await _generate_play(session, request, state=effective_state, seed=effective_seed)


async def generate_play_from_url(
    db_url: str,
    request: GenerationRequest,
    *,
    state: State | None = None,
    seed: int | None = None,
):
    """Generate a play by creating an engine/session for the given DB URL."""

    engine = create_engine(db_url)
    session_maker = create_sessionmaker(engine)
    async with session_scope(session_maker) as session:
        result = await generate_play(session, request, state=state, seed=seed)
    await engine.dispose()
    return result
