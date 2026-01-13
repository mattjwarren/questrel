import random

from questrel.models.enums import SelectionMode, SingleSelectStrategy
from questrel.models.state import State
from questrel.models.story import ScriptEdge
from questrel.runtime.branching import resolve_edges


def test_branching_priority_and_order() -> None:
    state = State(flags={"ok": True})
    edges = [
        ScriptEdge(
            edge_id="e1",
            from_node_id="a",
            to_node_id="b",
            when='state.flags["ok"] == True',
            priority=1,
            order_index=2,
            selection_mode=SelectionMode.MULTI,
        ),
        ScriptEdge(
            edge_id="e2",
            from_node_id="a",
            to_node_id="c",
            when='state.flags["ok"] == True',
            priority=1,
            order_index=1,
            selection_mode=SelectionMode.MULTI,
        ),
        # Lower priority should be ignored.
        ScriptEdge(
            edge_id="e3",
            from_node_id="a",
            to_node_id="d",
            when=None,
            priority=0,
            order_index=0,
            selection_mode=SelectionMode.MULTI,
        ),
    ]

    resolved = resolve_edges(edges, state=state)
    assert [e.edge_id for e in resolved] == ["e2", "e1"]


def test_single_weighted_is_deterministic() -> None:
    state = State(flags={"ok": True})
    edges = [
        ScriptEdge(
            edge_id="s1",
            from_node_id="a",
            to_node_id="b",
            when='state.flags["ok"] == True',
            priority=5,
            order_index=0,
            weight=1.0,
            selection_mode=SelectionMode.SINGLE,
        ),
        ScriptEdge(
            edge_id="s2",
            from_node_id="a",
            to_node_id="c",
            when='state.flags["ok"] == True',
            priority=5,
            order_index=1,
            weight=10.0,
            selection_mode=SelectionMode.SINGLE,
        ),
    ]

    rng = random.Random(123)
    resolved = resolve_edges(edges, state=state, strategy=SingleSelectStrategy.WEIGHTED, rng=rng)
    # With seed 123 and these weights, selection should be stable.
    assert len(resolved) == 1
    assert resolved[0].edge_id == "s1"
