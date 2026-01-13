"""Bindings between template requirements and concrete resources."""

from __future__ import annotations

from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class CharacterBinding:
    role_type: str
    character_id: str
    character_slug: str
    display_name: str


@dataclass(frozen=True)
class LocationBinding:
    location_id: str
    location_slug: str
    display_name: str


@dataclass(frozen=True)
class PropBinding:
    prop_id: str
    prop_slug: str
    display_name: str
