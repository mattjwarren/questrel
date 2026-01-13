"""Portable storage types.

Phase B requires storing JSON as TEXT in SQLite while exposing it as Python
dict/list values. This enables a later Postgres JSONB migration without changing
repository or generator code.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator


class JsonText(TypeDecorator):
    """JSON stored as TEXT, represented as Python objects."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect) -> str | None:  # noqa: ANN001
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    def process_result_value(self, value: str | None, dialect):  # noqa: ANN001
        if value is None:
            return None
        return json.loads(value)
