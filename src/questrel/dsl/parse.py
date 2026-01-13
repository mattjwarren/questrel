"""Parsing for the Questrel condition DSL."""

from __future__ import annotations

import ast

from .errors import DSLParseError


def parse_expression(expr: str) -> ast.Expression:
    """Parse an expression string into an AST Expression."""

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise DSLParseError(str(exc)) from exc

    if not isinstance(tree, ast.Expression):
        # Defensive: ast.parse(mode='eval') should always return Expression.
        raise DSLParseError("Expression did not parse as an AST Expression")

    return tree
