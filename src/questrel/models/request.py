"""Request models for generation."""

from __future__ import annotations

from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class GenerationRequest:
    """Inputs from a consuming game.

    MVP focuses on counts. Tags/filters can be added in later iterations.
    """

    max_characters: int
    location_count: int
    prop_count: int = 0

    # Optional template selection override.
    template_key: str | None = None

    # Determinism: if not provided, caller can pass seed to `generate_play`.
    seed: int | None = None
