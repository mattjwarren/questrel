"""Story graph models for Questrel."""

from __future__ import annotations

from pydantic.dataclasses import dataclass

from .enums import SelectionMode


@dataclass(frozen=True)
class ScriptNode:
    node_id: str
    node_type: str
    text: str | None = None
    metadata: dict = None  # JSON-like payload

    def __post_init__(self) -> None:
        # Pydantic dataclasses allow post-init.
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


@dataclass(frozen=True)
class ScriptEdge:
    """A transition between nodes.

    - `when` is a condition expression in the Questrel DSL.
    - `selection_mode` is stored per edge.
    """

    edge_id: str
    from_node_id: str
    to_node_id: str

    when: str | None = None
    priority: int = 0
    order_index: int = 0
    weight: float = 1.0
    selection_mode: SelectionMode = SelectionMode.SINGLE
