"""Deterministic randomness helpers.

Questrel needs reproducible selection for testing and game replay.
"""

from __future__ import annotations

import hashlib
import random
from typing import Any


def derive_seed(*parts: Any) -> int:
    """Derive a stable 64-bit seed from arbitrary parts.

    This uses SHA-256 over a UTF-8 representation of the provided parts.
    """

    payload = "|".join(str(p) for p in parts).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    # Take the first 8 bytes as a stable 64-bit integer.
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def rng_from_seed(seed: int) -> random.Random:
    """Create a deterministic RNG from a seed."""

    return random.Random(seed)


def rng_for_decision(
    *,
    base_seed: int,
    template_id: str,
    node_id: str,
    decision_index: int,
) -> random.Random:
    """Create a per-decision deterministic RNG."""

    return rng_from_seed(derive_seed(base_seed, template_id, node_id, decision_index))
