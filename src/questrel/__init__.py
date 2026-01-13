"""Questrel library.

Phase A provides:
- Safe condition DSL restricted to `state.flags["x"]` lookups.
- Deterministic branching resolution over a list of edges.
"""

from .models.enums import SelectionMode, SingleSelectStrategy
from .models.request import GenerationRequest
from .models.generated import GeneratedPlay
from .models.state import State
from .models.story import ScriptEdge, ScriptNode
from .api import generate_play, generate_play_from_url
from .runtime.branching import resolve_edges

__all__ = [
    "GeneratedPlay",
    "GenerationRequest",
    "ScriptEdge",
    "ScriptNode",
    "SelectionMode",
    "SingleSelectStrategy",
    "State",
    "generate_play",
    "generate_play_from_url",
    "resolve_edges",
]
