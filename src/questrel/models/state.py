"""Runtime state model.

MVP design:
- All condition logic reads from `state.flags`.
- Keys are permanently `str` only.
- Missing keys in DSL evaluate as `None`.
"""

from __future__ import annotations

from typing import TypeAlias

from pydantic.dataclasses import dataclass


Scalar: TypeAlias = bool | int | float | str | None


@dataclass(frozen=True)
class State:
    """Runtime play state exposed to the DSL."""

    flags: dict[str, Scalar]

    def get_flag(self, key: str) -> Scalar:
        """Return a flag value; returns None when missing."""

        return self.flags.get(key)
