"""Branching resolution logic.

Phase A implements the resolver over a list of edges.

Rules:
- Filter edges by condition (DSL), treating missing flags as None.
- Sort by priority desc then order_index asc.
- Keep only highest-priority tier.
- Return MULTI edges + at most one SINGLE edge.
- If no valid edges: return [].
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from ..dsl.eval import evaluate
from ..logging import get_logger
from ..models.enums import SelectionMode, SingleSelectStrategy
from ..models.state import State
from ..models.story import ScriptEdge


logger = get_logger("branching")


def resolve_edges(
    edges: Sequence[ScriptEdge],
    *,
    state: State,
    strategy: SingleSelectStrategy = SingleSelectStrategy.FIRST,
    rng: random.Random | None = None,
) -> list[ScriptEdge]:
    """Resolve outgoing edges for a decision step.

    Returns a list (possibly empty) of selected edges.
    """

    valid: list[ScriptEdge] = []
    for edge in edges:
        if edge.when is None:
            valid.append(edge)
            continue
        if evaluate(edge.when, state=state):
            valid.append(edge)

    if not valid:
        return []

    valid_sorted = sorted(valid, key=_edge_sort_key)
    top_priority = valid_sorted[0].priority
    tier = [e for e in valid_sorted if e.priority == top_priority]

    multi_edges = [e for e in tier if e.selection_mode == SelectionMode.MULTI]
    single_edges = [e for e in tier if e.selection_mode == SelectionMode.SINGLE]

    chosen_single: ScriptEdge | None = None
    if single_edges:
        chosen_single = _choose_single(single_edges, strategy=strategy, rng=rng)

    selected = list(multi_edges)
    if chosen_single is not None:
        selected.append(chosen_single)

    # Ensure output order is stable.
    return sorted(selected, key=_edge_sort_key)


def _edge_sort_key(edge: ScriptEdge) -> tuple:
    # priority desc, then order asc, then edge_id asc
    return (-edge.priority, edge.order_index, edge.edge_id)


def _choose_single(
    edges: Sequence[ScriptEdge],
    *,
    strategy: SingleSelectStrategy,
    rng: random.Random | None,
) -> ScriptEdge:
    if strategy == SingleSelectStrategy.FIRST:
        return sorted(edges, key=_edge_sort_key)[0]

    if rng is None:
        logger.warning("No RNG provided for %s; using non-deterministic RNG", strategy)
        rng = random.Random()

    if strategy == SingleSelectStrategy.RANDOM:
        return rng.choice(list(edges))

    if strategy == SingleSelectStrategy.WEIGHTED:
        weighted = [(e, float(e.weight)) for e in edges if float(e.weight) > 0]
        if not weighted:
            return sorted(edges, key=_edge_sort_key)[0]

        total = sum(w for _, w in weighted)
        roll = rng.random() * total
        acc = 0.0
        for edge, weight in weighted:
            acc += weight
            if roll <= acc:
                return edge
        return weighted[-1][0]

    return sorted(edges, key=_edge_sort_key)[0]
