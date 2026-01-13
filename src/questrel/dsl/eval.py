"""Evaluation for Questrel DSL expressions.

Evaluation is performed by interpreting a validated AST.
"""

from __future__ import annotations

import ast

from ..logging import get_logger
from ..models.state import State
from .errors import DSLEvaluationError
from .validate import CompiledExpression, compile_expression


logger = get_logger("dsl")


def evaluate(expr: str | CompiledExpression, *, state: State) -> bool:
    """Evaluate an expression against the provided state.

    Any evaluation error yields False (and is logged) to keep runtime robust.
    """

    compiled = compile_expression(expr) if isinstance(expr, str) else expr

    try:
        value = _eval_node(compiled.tree.body, state)
        return bool(value)
    except Exception as exc:  # noqa: BLE001 - deliberate robustness boundary
        logger.warning("DSL evaluation failed for %r: %s", compiled.source, exc)
        return False


def _eval_node(node: ast.AST, state: State):
    match node:
        case ast.BoolOp(op=op, values=values):
            if isinstance(op, ast.And):
                for v in values:
                    if not bool(_eval_node(v, state)):
                        return False
                return True
            if isinstance(op, ast.Or):
                for v in values:
                    if bool(_eval_node(v, state)):
                        return True
                return False
            raise DSLEvaluationError("Unsupported boolean operator")

        case ast.UnaryOp(op=op, operand=operand):
            if isinstance(op, ast.Not):
                return not bool(_eval_node(operand, state))
            raise DSLEvaluationError("Unsupported unary operator")

        case ast.Compare(left=left, ops=ops, comparators=comparators):
            current = _eval_node(left, state)
            for op, comp_node in zip(ops, comparators, strict=False):
                target = _eval_node(comp_node, state)
                if not _compare(current, op, target):
                    return False
                current = target
            return True

        case ast.Name(id=name):
            if name == "state":
                return state
            raise DSLEvaluationError("Unknown name")

        case ast.Attribute(value=value, attr=attr):
            # Only `state.flags` can exist due to validation.
            if isinstance(value, ast.Name) and value.id == "state" and attr == "flags":
                return state.flags
            raise DSLEvaluationError("Unsupported attribute")

        case ast.Subscript(value=value, slice=slice_node):
            container = _eval_node(value, state)
            if not isinstance(container, dict):
                return None
            key = _eval_node(slice_node, state)
            if not isinstance(key, str):
                return None
            # Missing keys must evaluate as None.
            return container.get(key)

        case ast.Constant(value=v):
            return v

        case ast.List(elts=elts):
            return [_eval_node(e, state) for e in elts]

        case ast.Tuple(elts=elts):
            return tuple(_eval_node(e, state) for e in elts)

        case _:
            raise DSLEvaluationError(f"Unsupported node: {type(node).__name__}")


def _compare(left, op: ast.cmpop, right) -> bool:
    """Safe comparisons.

    For invalid comparisons (TypeError), return False.
    """

    try:
        if isinstance(op, ast.Eq):
            return left == right
        if isinstance(op, ast.NotEq):
            return left != right
        if isinstance(op, ast.Lt):
            return left < right
        if isinstance(op, ast.LtE):
            return left <= right
        if isinstance(op, ast.Gt):
            return left > right
        if isinstance(op, ast.GtE):
            return left >= right
        if isinstance(op, ast.In):
            return left in right
        if isinstance(op, ast.NotIn):
            return left not in right
    except TypeError:
        return False

    raise DSLEvaluationError("Unsupported comparison")
