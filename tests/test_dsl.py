import pytest


from questrel.dsl.eval import evaluate
from questrel.dsl.validate import compile_expression
from questrel.models.state import State


def test_missing_key_is_none() -> None:
    state = State(flags={})
    assert evaluate('state.flags["x"] == None', state=state) is True
    assert evaluate('state.flags["x"] != None', state=state) is False


def test_mixed_scalar_comparisons() -> None:
    state = State(flags={"reputation": 10, "faction": "mages", "met_mayor": True})
    assert evaluate('state.flags["reputation"] >= 10', state=state) is True
    assert evaluate('state.flags["faction"] in ["mages", "thieves"]', state=state) is True
    assert evaluate('state.flags["met_mayor"] == True', state=state) is True


def test_invalid_function_call_rejected() -> None:
    with pytest.raises(Exception):
        compile_expression('__import__("os")')


def test_non_string_key_rejected() -> None:
    with pytest.raises(Exception):
        compile_expression('state.flags[1] == None')
