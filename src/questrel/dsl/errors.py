"""DSL error types."""

from __future__ import annotations


class DSLParseError(ValueError):
    pass


class DSLValidationError(ValueError):
    pass


class DSLEvaluationError(RuntimeError):
    pass
