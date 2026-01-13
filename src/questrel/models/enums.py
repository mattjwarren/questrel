"""Core enums for Questrel models."""

from __future__ import annotations

from enum import StrEnum


class SelectionMode(StrEnum):
    """Selection cardinality for an edge or pool item."""

    SINGLE = "single"
    MULTI = "multi"


class SingleSelectStrategy(StrEnum):
    """Strategy used when choosing among SINGLE edges/items."""

    FIRST = "first"
    RANDOM = "random"
    WEIGHTED = "weighted"
