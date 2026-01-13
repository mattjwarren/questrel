"""Initial Questrel schema.

Revision ID: 20260113_0001
Revises: 
Create Date: 2026-01-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260113_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "play_template",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version_int", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("key", name="uq_play_template_key"),
    )

    op.create_table(
        "condition_expression",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("template_id", sa.String(), sa.ForeignKey("play_template.id"), nullable=False),
        sa.Column("language", sa.String(), nullable=False, server_default="questrel_expr"),
        sa.Column("version_int", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("expr_text", sa.Text(), nullable=False),
    )

    op.create_table(
        "script_node",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("template_id", sa.String(), sa.ForeignKey("play_template.id"), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("node_type", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.UniqueConstraint("template_id", "key", name="uq_script_node_template_key"),
    )

    op.create_table(
        "script_edge",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("template_id", sa.String(), sa.ForeignKey("play_template.id"), nullable=False),
        sa.Column("from_node_id", sa.String(), sa.ForeignKey("script_node.id"), nullable=False),
        sa.Column("to_node_id", sa.String(), sa.ForeignKey("script_node.id"), nullable=False),
        sa.Column("when_expr_id", sa.String(), sa.ForeignKey("condition_expression.id"), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("selection_mode", sa.String(), nullable=False, server_default="single"),
    )

    op.create_table(
        "tag",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.UniqueConstraint("name", name="uq_tag_name"),
    )

    op.create_table(
        "character_resource",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("base_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("rarity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("slug", name="uq_character_resource_slug"),
    )

    op.create_table(
        "location_resource",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("base_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("rarity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("slug", name="uq_location_resource_slug"),
    )

    op.create_table(
        "prop_resource",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("base_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("rarity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("slug", name="uq_prop_resource_slug"),
    )

    op.create_table(
        "character_resource_tag",
        sa.Column("resource_id", sa.String(), sa.ForeignKey("character_resource.id"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tag.id"), primary_key=True),
    )
    op.create_table(
        "location_resource_tag",
        sa.Column("resource_id", sa.String(), sa.ForeignKey("location_resource.id"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tag.id"), primary_key=True),
    )
    op.create_table(
        "prop_resource_tag",
        sa.Column("resource_id", sa.String(), sa.ForeignKey("prop_resource.id"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tag.id"), primary_key=True),
    )

    op.create_table(
        "resource_pool",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("template_id", sa.String(), sa.ForeignKey("play_template.id"), nullable=True),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("template_id", "key", name="uq_resource_pool_template_key"),
    )

    op.create_table(
        "character_pool_item",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("pool_id", sa.String(), sa.ForeignKey("resource_pool.id"), nullable=False),
        sa.Column("resource_id", sa.String(), sa.ForeignKey("character_resource.id"), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("condition_expr_id", sa.String(), sa.ForeignKey("condition_expression.id"), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("selection_mode", sa.String(), nullable=False, server_default="single"),
        sa.UniqueConstraint("pool_id", "resource_id", name="uq_character_pool_item_pool_resource"),
    )
    op.create_table(
        "location_pool_item",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("pool_id", sa.String(), sa.ForeignKey("resource_pool.id"), nullable=False),
        sa.Column("resource_id", sa.String(), sa.ForeignKey("location_resource.id"), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("condition_expr_id", sa.String(), sa.ForeignKey("condition_expression.id"), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("selection_mode", sa.String(), nullable=False, server_default="single"),
        sa.UniqueConstraint("pool_id", "resource_id", name="uq_location_pool_item_pool_resource"),
    )
    op.create_table(
        "prop_pool_item",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("pool_id", sa.String(), sa.ForeignKey("resource_pool.id"), nullable=False),
        sa.Column("resource_id", sa.String(), sa.ForeignKey("prop_resource.id"), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("condition_expr_id", sa.String(), sa.ForeignKey("condition_expression.id"), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("selection_mode", sa.String(), nullable=False, server_default="single"),
        sa.UniqueConstraint("pool_id", "resource_id", name="uq_prop_pool_item_pool_resource"),
    )

    op.create_table(
        "template_role_requirement",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("template_id", sa.String(), sa.ForeignKey("play_template.id"), nullable=False),
        sa.Column("role_type", sa.String(), nullable=False),
        sa.Column("count_min", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("count_max", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("constraints_json", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("template_id", "role_type", name="uq_template_role_req_template_role"),
    )

    op.create_table(
        "template_location_requirement",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("template_id", sa.String(), sa.ForeignKey("play_template.id"), nullable=False),
        sa.Column("count_min", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("count_max", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("constraints_json", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "template_prop_requirement",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("template_id", sa.String(), sa.ForeignKey("play_template.id"), nullable=False),
        sa.Column("count_min", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("count_max", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("constraints_json", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "template_role_req_tag_required",
        sa.Column("requirement_id", sa.String(), sa.ForeignKey("template_role_requirement.id"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tag.id"), primary_key=True),
    )
    op.create_table(
        "template_role_req_tag_forbidden",
        sa.Column("requirement_id", sa.String(), sa.ForeignKey("template_role_requirement.id"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tag.id"), primary_key=True),
    )
    op.create_table(
        "template_location_req_tag_required",
        sa.Column(
            "requirement_id", sa.String(), sa.ForeignKey("template_location_requirement.id"), primary_key=True
        ),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tag.id"), primary_key=True),
    )
    op.create_table(
        "template_location_req_tag_forbidden",
        sa.Column(
            "requirement_id", sa.String(), sa.ForeignKey("template_location_requirement.id"), primary_key=True
        ),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tag.id"), primary_key=True),
    )
    op.create_table(
        "template_prop_req_tag_required",
        sa.Column("requirement_id", sa.String(), sa.ForeignKey("template_prop_requirement.id"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tag.id"), primary_key=True),
    )
    op.create_table(
        "template_prop_req_tag_forbidden",
        sa.Column("requirement_id", sa.String(), sa.ForeignKey("template_prop_requirement.id"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tag.id"), primary_key=True),
    )


def downgrade() -> None:
    # Drop in reverse dependency order.
    op.drop_table("template_prop_req_tag_forbidden")
    op.drop_table("template_prop_req_tag_required")
    op.drop_table("template_location_req_tag_forbidden")
    op.drop_table("template_location_req_tag_required")
    op.drop_table("template_role_req_tag_forbidden")
    op.drop_table("template_role_req_tag_required")
    op.drop_table("template_prop_requirement")
    op.drop_table("template_location_requirement")
    op.drop_table("template_role_requirement")
    op.drop_table("prop_pool_item")
    op.drop_table("location_pool_item")
    op.drop_table("character_pool_item")
    op.drop_table("resource_pool")
    op.drop_table("prop_resource_tag")
    op.drop_table("location_resource_tag")
    op.drop_table("character_resource_tag")
    op.drop_table("prop_resource")
    op.drop_table("location_resource")
    op.drop_table("character_resource")
    op.drop_table("tag")
    op.drop_table("script_edge")
    op.drop_table("script_node")
    op.drop_table("condition_expression")
    op.drop_table("play_template")
