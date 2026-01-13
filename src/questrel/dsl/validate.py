"""Validation for the Questrel condition DSL.

The DSL is intentionally restrictive and safe:
- Only `state.flags["x"]` lookups are allowed.
- No function calls, attribute access, imports, comprehensions, etc.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from ..logging import get_logger
from .errors import DSLValidationError
from .parse import parse_expression


logger = get_logger("dsl")


@dataclass(frozen=True)
class CompiledExpression:
    """A validated expression ready for evaluation."""

    source: str
    tree: ast.Expression
    referenced_flags: frozenset[str]


DEFAULT_MAX_LEN = 8192
DEFAULT_MAX_NODES = 1024
DEFAULT_MAX_DEPTH = 48


_ALLOWED_COMPARE_OPS = (
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
)


def compile_expression(
    expr: str,
    *,
    max_len: int = DEFAULT_MAX_LEN,
    max_nodes: int = DEFAULT_MAX_NODES,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> CompiledExpression:
    """Parse and validate an expression, returning a compiled form."""

    if len(expr) > max_len:
        raise DSLValidationError(f"Expression too long (>{max_len} chars)")

    tree = parse_expression(expr)

    node_count = _count_nodes(tree)
    if node_count > max_nodes:
        raise DSLValidationError(f"Expression too complex (>{max_nodes} AST nodes)")

    depth = _max_depth(tree)
    if depth > max_depth:
        raise DSLValidationError(f"Expression nesting too deep (>{max_depth})")

    referenced_flags: set[str] = set()
    _validate_node(tree.body, referenced_flags)

    return CompiledExpression(source=expr, tree=tree, referenced_flags=frozenset(referenced_flags))


def _count_nodes(node: ast.AST) -> int:
    return sum(1 for _ in ast.walk(node))


def _max_depth(node: ast.AST) -> int:
    """Compute maximum AST depth."""

    def rec(n: ast.AST, depth: int) -> int:
        child_depths = [rec(c, depth + 1) for c in ast.iter_child_nodes(n)]
        return max([depth, *child_depths])

    return rec(node, 0)


def _validate_node(node: ast.AST, referenced_flags: set[str]) -> None:
    """Validate node is within allowlist and matches `state.flags["x"]` pattern."""

    match node:
        case ast.BoolOp(op=op, values=values):
            if not isinstance(op, (ast.And, ast.Or)):
                raise DSLValidationError("Only 'and'/'or' boolean ops are allowed")
            for v in values:
                _validate_node(v, referenced_flags)

        case ast.UnaryOp(op=op, operand=operand):
            if not isinstance(op, ast.Not):
                raise DSLValidationError("Only 'not' unary op is allowed")
            _validate_node(operand, referenced_flags)

        case ast.Compare(left=left, ops=ops, comparators=comparators):
            _validate_node(left, referenced_flags)
            for op in ops:
                if not isinstance(op, _ALLOWED_COMPARE_OPS):
                    raise DSLValidationError("Unsupported comparison operator")
            for c in comparators:
                _validate_node(c, referenced_flags)

        case ast.Name(id=name):
            if name != "state":
                raise DSLValidationError("Only the name 'state' is allowed")

        case ast.Attribute(value=value, attr=attr):
            # Only allow `state.flags`.
            if not (isinstance(value, ast.Name) and value.id == "state" and attr == "flags"):
                raise DSLValidationError("Only attribute access 'state.flags' is allowed")

        case ast.Subscript(value=value, slice=slice_node):
            # Only allow `state.flags["key"]`.
            if not (
                isinstance(value, ast.Attribute)
                and isinstance(value.value, ast.Name)
                and value.value.id == "state"
                and value.attr == "flags"
            ):
                raise DSLValidationError("Only subscripts of the form state.flags[\"x\"] are allowed")

            key = _extract_subscript_key(slice_node)
            referenced_flags.add(key)

        case ast.Constant(value=v):
            if not isinstance(v, (type(None), bool, int, float, str)):
                raise DSLValidationError("Unsupported constant type")

        case ast.List(elts=elts) | ast.Tuple(elts=elts):
            for e in elts:
                _validate_node(e, referenced_flags)

        case _:
            raise DSLValidationError(f"Unsupported expression element: {type(node).__name__}")


def _extract_subscript_key(slice_node: ast.AST) -> str:
    # Python 3.11 uses slice expressions directly.
    if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
        return slice_node.value

    raise DSLValidationError("Subscript key must be a string literal, e.g. state.flags[\"x\"]")
