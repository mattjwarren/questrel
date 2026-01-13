"""Generated output models."""

from __future__ import annotations

from pydantic import TypeAdapter
from pydantic.dataclasses import dataclass

from .bindings import CharacterBinding, LocationBinding, PropBinding
from .story import ScriptEdge, ScriptNode


@dataclass(frozen=True)
class GeneratedPlay:
    """A fully generated play/quest output."""

    generated_id: str
    template_id: str
    seed: int
    nodes: list[ScriptNode]
    edges: list[ScriptEdge]
    characters: list[CharacterBinding]
    locations: list[LocationBinding]
    props: list[PropBinding]
    metadata: dict | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

    def model_dump(self) -> dict:
        """Return a JSON-serializable dict representation."""

        adapter = TypeAdapter(self.__class__)
        return adapter.dump_python(self, mode="json", exclude_none=True)

    def model_dump_json(self) -> str:
        """Return a JSON string representation."""

        adapter = TypeAdapter(self.__class__)
        return adapter.dump_json(self, exclude_none=True).decode("utf-8")
