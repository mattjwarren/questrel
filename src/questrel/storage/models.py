"""SQLAlchemy ORM models (Phase B).

This schema supports:
- Templates
- Script graph (nodes/edges) with branching conditions
- Resource catalogs (characters/locations/props) with tags
- Resource pools and weighted pool items with optional conditional expressions
- Template requirements for roles/locations/props

All metadata/spec/constraints fields are stored as JSON-as-TEXT via JsonText.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from ..models.enums import SelectionMode
from .types import JsonText


class Base(DeclarativeBase):
    pass


class PlayTemplate(Base):
    __tablename__ = "play_template"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    key: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version_int: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint("key", name="uq_play_template_key"),)


class ConditionExpression(Base):
    __tablename__ = "condition_expression"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    template_id: Mapped[str] = mapped_column(ForeignKey("play_template.id"), nullable=False)
    language: Mapped[str] = mapped_column(String, default="questrel_expr")
    version_int: Mapped[int] = mapped_column(Integer, default=1)
    expr_text: Mapped[str] = mapped_column(Text, nullable=False)

    template: Mapped[PlayTemplate] = relationship()


class ScriptNode(Base):
    __tablename__ = "script_node"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    template_id: Mapped[str] = mapped_column(ForeignKey("play_template.id"), nullable=False)
    key: Mapped[str] = mapped_column(String, nullable=False)
    node_type: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JsonText, nullable=True)

    template: Mapped[PlayTemplate] = relationship()

    __table_args__ = (UniqueConstraint("template_id", "key", name="uq_script_node_template_key"),)


class ScriptEdge(Base):
    __tablename__ = "script_edge"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    template_id: Mapped[str] = mapped_column(ForeignKey("play_template.id"), nullable=False)

    from_node_id: Mapped[str] = mapped_column(ForeignKey("script_node.id"), nullable=False)
    to_node_id: Mapped[str] = mapped_column(ForeignKey("script_node.id"), nullable=False)

    when_expr_id: Mapped[str | None] = mapped_column(ForeignKey("condition_expression.id"), nullable=True)

    priority: Mapped[int] = mapped_column(Integer, default=0)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    selection_mode: Mapped[str] = mapped_column(String, default=SelectionMode.SINGLE.value)

    template: Mapped[PlayTemplate] = relationship()
    when_expr: Mapped[ConditionExpression | None] = relationship(foreign_keys=[when_expr_id])
    from_node: Mapped[ScriptNode] = relationship(foreign_keys=[from_node_id])
    to_node: Mapped[ScriptNode] = relationship(foreign_keys=[to_node_id])


class Tag(Base):
    __tablename__ = "tag"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (UniqueConstraint("name", name="uq_tag_name"),)


class CharacterResource(Base):
    __tablename__ = "character_resource"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    slug: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JsonText, nullable=True)
    base_weight: Mapped[float] = mapped_column(Float, default=1.0)
    rarity: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (UniqueConstraint("slug", name="uq_character_resource_slug"),)


class LocationResource(Base):
    __tablename__ = "location_resource"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    slug: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JsonText, nullable=True)
    base_weight: Mapped[float] = mapped_column(Float, default=1.0)
    rarity: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (UniqueConstraint("slug", name="uq_location_resource_slug"),)


class PropResource(Base):
    __tablename__ = "prop_resource"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    slug: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JsonText, nullable=True)
    base_weight: Mapped[float] = mapped_column(Float, default=1.0)
    rarity: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (UniqueConstraint("slug", name="uq_prop_resource_slug"),)


class CharacterResourceTag(Base):
    __tablename__ = "character_resource_tag"
    resource_id: Mapped[str] = mapped_column(ForeignKey("character_resource.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)


class LocationResourceTag(Base):
    __tablename__ = "location_resource_tag"
    resource_id: Mapped[str] = mapped_column(ForeignKey("location_resource.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)


class PropResourceTag(Base):
    __tablename__ = "prop_resource_tag"
    resource_id: Mapped[str] = mapped_column(ForeignKey("prop_resource.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)


class ResourcePool(Base):
    __tablename__ = "resource_pool"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    template_id: Mapped[str | None] = mapped_column(ForeignKey("play_template.id"), nullable=True)
    key: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # character|location|prop
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JsonText, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    template: Mapped[PlayTemplate | None] = relationship()

    __table_args__ = (UniqueConstraint("template_id", "key", name="uq_resource_pool_template_key"),)


class CharacterPoolItem(Base):
    __tablename__ = "character_pool_item"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    pool_id: Mapped[str] = mapped_column(ForeignKey("resource_pool.id"), nullable=False)
    resource_id: Mapped[str] = mapped_column(ForeignKey("character_resource.id"), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    condition_expr_id: Mapped[str | None] = mapped_column(ForeignKey("condition_expression.id"), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JsonText, nullable=True)
    selection_mode: Mapped[str] = mapped_column(String, default=SelectionMode.SINGLE.value)

    pool: Mapped[ResourcePool] = relationship()
    resource: Mapped[CharacterResource] = relationship()
    condition_expr: Mapped[ConditionExpression | None] = relationship(foreign_keys=[condition_expr_id])

    __table_args__ = (UniqueConstraint("pool_id", "resource_id", name="uq_character_pool_item_pool_resource"),)


class LocationPoolItem(Base):
    __tablename__ = "location_pool_item"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    pool_id: Mapped[str] = mapped_column(ForeignKey("resource_pool.id"), nullable=False)
    resource_id: Mapped[str] = mapped_column(ForeignKey("location_resource.id"), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    condition_expr_id: Mapped[str | None] = mapped_column(ForeignKey("condition_expression.id"), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JsonText, nullable=True)
    selection_mode: Mapped[str] = mapped_column(String, default=SelectionMode.SINGLE.value)

    pool: Mapped[ResourcePool] = relationship()
    resource: Mapped[LocationResource] = relationship()
    condition_expr: Mapped[ConditionExpression | None] = relationship(foreign_keys=[condition_expr_id])

    __table_args__ = (UniqueConstraint("pool_id", "resource_id", name="uq_location_pool_item_pool_resource"),)


class PropPoolItem(Base):
    __tablename__ = "prop_pool_item"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    pool_id: Mapped[str] = mapped_column(ForeignKey("resource_pool.id"), nullable=False)
    resource_id: Mapped[str] = mapped_column(ForeignKey("prop_resource.id"), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    condition_expr_id: Mapped[str | None] = mapped_column(ForeignKey("condition_expression.id"), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JsonText, nullable=True)
    selection_mode: Mapped[str] = mapped_column(String, default=SelectionMode.SINGLE.value)

    pool: Mapped[ResourcePool] = relationship()
    resource: Mapped[PropResource] = relationship()
    condition_expr: Mapped[ConditionExpression | None] = relationship(foreign_keys=[condition_expr_id])

    __table_args__ = (UniqueConstraint("pool_id", "resource_id", name="uq_prop_pool_item_pool_resource"),)


class TemplateRoleRequirement(Base):
    __tablename__ = "template_role_requirement"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    template_id: Mapped[str] = mapped_column(ForeignKey("play_template.id"), nullable=False)
    role_type: Mapped[str] = mapped_column(String, nullable=False)
    count_min: Mapped[int] = mapped_column(Integer, default=1)
    count_max: Mapped[int] = mapped_column(Integer, default=1)
    constraints_json: Mapped[dict | None] = mapped_column(JsonText, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    template: Mapped[PlayTemplate] = relationship()

    __table_args__ = (UniqueConstraint("template_id", "role_type", name="uq_template_role_req_template_role"),)


class TemplateLocationRequirement(Base):
    __tablename__ = "template_location_requirement"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    template_id: Mapped[str] = mapped_column(ForeignKey("play_template.id"), nullable=False)
    count_min: Mapped[int] = mapped_column(Integer, default=1)
    count_max: Mapped[int] = mapped_column(Integer, default=1)
    constraints_json: Mapped[dict | None] = mapped_column(JsonText, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    template: Mapped[PlayTemplate] = relationship()


class TemplatePropRequirement(Base):
    __tablename__ = "template_prop_requirement"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    template_id: Mapped[str] = mapped_column(ForeignKey("play_template.id"), nullable=False)
    count_min: Mapped[int] = mapped_column(Integer, default=0)
    count_max: Mapped[int] = mapped_column(Integer, default=0)
    constraints_json: Mapped[dict | None] = mapped_column(JsonText, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    template: Mapped[PlayTemplate] = relationship()


class TemplateRoleReqTagRequired(Base):
    __tablename__ = "template_role_req_tag_required"
    requirement_id: Mapped[str] = mapped_column(ForeignKey("template_role_requirement.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)


class TemplateRoleReqTagForbidden(Base):
    __tablename__ = "template_role_req_tag_forbidden"
    requirement_id: Mapped[str] = mapped_column(ForeignKey("template_role_requirement.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)


class TemplateLocationReqTagRequired(Base):
    __tablename__ = "template_location_req_tag_required"
    requirement_id: Mapped[str] = mapped_column(ForeignKey("template_location_requirement.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)


class TemplateLocationReqTagForbidden(Base):
    __tablename__ = "template_location_req_tag_forbidden"
    requirement_id: Mapped[str] = mapped_column(ForeignKey("template_location_requirement.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)


class TemplatePropReqTagRequired(Base):
    __tablename__ = "template_prop_req_tag_required"
    requirement_id: Mapped[str] = mapped_column(ForeignKey("template_prop_requirement.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)


class TemplatePropReqTagForbidden(Base):
    __tablename__ = "template_prop_req_tag_forbidden"
    requirement_id: Mapped[str] = mapped_column(ForeignKey("template_prop_requirement.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)
