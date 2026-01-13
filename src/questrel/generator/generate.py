"""End-to-end generation for Phase C.

This is intentionally a small MVP:
- Select a suitable template by basic count constraints.
- Load graph nodes/edges from storage.
- Bind characters/locations/props by sampling from resource pools.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from ..dsl.eval import evaluate
from ..logging import get_logger
from ..models.bindings import CharacterBinding, LocationBinding, PropBinding
from ..models.enums import SelectionMode
from ..models.generated import GeneratedPlay
from ..models.request import GenerationRequest
from ..models.state import State
from ..models.story import ScriptEdge as DomainEdge
from ..models.story import ScriptNode as DomainNode
from ..random.deterministic import derive_seed, rng_from_seed
from ..storage.models import (
    CharacterPoolItem,
    LocationPoolItem,
    PlayTemplate,
    PropPoolItem,
    ResourcePool,
    ScriptEdge,
    ScriptNode,
    TemplateLocationRequirement,
    TemplatePropRequirement,
    TemplateRoleRequirement,
)
from ..storage.repositories.graph_repo import GraphRepository
from ..storage.repositories.pool_repo import PoolRepository
from ..storage.repositories.template_repo import TemplateRepository


logger = get_logger("generator")


class NoMatchingTemplateError(RuntimeError):
    pass


@dataclass(frozen=True)
class _Counts:
    characters_min: int
    characters_max: int
    locations_min: int
    locations_max: int
    props_min: int
    props_max: int


async def generate_play(
    session: AsyncSession,
    request: GenerationRequest,
    *,
    state: State,
    seed: int,
) -> GeneratedPlay:
    template = await _select_template(session, request, seed=seed)

    template_counts = await _template_counts(session, template.id)
    _validate_request_against_template(request, template_counts)

    graph_repo = GraphRepository(session)
    db_nodes = await graph_repo.list_nodes(template.id)
    db_edges = await graph_repo.list_edges(template.id)

    nodes = [_map_node(n) for n in db_nodes]
    edges = [_map_edge(e) for e in db_edges]

    bindings_seed = derive_seed(seed, template.id, "bindings")
    rng = rng_from_seed(bindings_seed)

    pool_repo = PoolRepository(session)
    characters = await _bind_characters(session, pool_repo, template.id, request, state, rng)
    locations = await _bind_locations(session, pool_repo, template.id, request, state, rng)
    props = await _bind_props(session, pool_repo, template.id, request, state, rng)

    return GeneratedPlay(
        generated_id=str(uuid.uuid4()),
        template_id=template.id,
        seed=seed,
        nodes=nodes,
        edges=edges,
        characters=characters,
        locations=locations,
        props=props,
        metadata={"template_key": template.key, "template_name": template.name},
    )


async def _select_template(session: AsyncSession, request: GenerationRequest, *, seed: int) -> PlayTemplate:
    template_repo = TemplateRepository(session)

    if request.template_key is not None:
        # Simple lookup by key.
        from sqlalchemy import select

        res = await session.execute(select(PlayTemplate).where(PlayTemplate.key == request.template_key))
        tpl = res.scalars().first()
        if tpl is None:
            raise NoMatchingTemplateError(f"No template found for key={request.template_key!r}")
        return tpl

    # MVP: choose a deterministic "random" template among those that satisfy constraints.
    from sqlalchemy import select

    res = await session.execute(select(PlayTemplate).order_by(PlayTemplate.created_at.asc()))
    candidates: list[PlayTemplate] = []
    for tpl in res.scalars().all():
        counts = await _template_counts(session, tpl.id)
        if counts.characters_min <= request.max_characters and counts.locations_min <= request.location_count:
            candidates.append(tpl)

    if candidates:
        rng = rng_from_seed(derive_seed(seed, "template_select"))
        return rng.choice(candidates)

    raise NoMatchingTemplateError("No template satisfies the requested constraints")


async def _template_counts(session: AsyncSession, template_id: str) -> _Counts:
    template_repo = TemplateRepository(session)

    role_reqs: list[TemplateRoleRequirement] = await template_repo.list_role_requirements(template_id)
    loc_reqs: list[TemplateLocationRequirement] = await template_repo.list_location_requirements(template_id)
    prop_reqs: list[TemplatePropRequirement] = await template_repo.list_prop_requirements(template_id)

    characters_min = sum(r.count_min for r in role_reqs) if role_reqs else 0
    characters_max = sum(r.count_max for r in role_reqs) if role_reqs else 0
    locations_min = sum(r.count_min for r in loc_reqs) if loc_reqs else 0
    locations_max = sum(r.count_max for r in loc_reqs) if loc_reqs else 0
    props_min = sum(r.count_min for r in prop_reqs) if prop_reqs else 0
    props_max = sum(r.count_max for r in prop_reqs) if prop_reqs else 0

    return _Counts(
        characters_min=characters_min,
        characters_max=characters_max,
        locations_min=locations_min,
        locations_max=locations_max,
        props_min=props_min,
        props_max=props_max,
    )


def _validate_request_against_template(request: GenerationRequest, counts: _Counts) -> None:
    if request.max_characters < counts.characters_min:
        raise NoMatchingTemplateError("Requested max_characters is less than template minimum")
    if request.location_count < counts.locations_min:
        raise NoMatchingTemplateError("Requested location_count is less than template minimum")
    if request.prop_count < counts.props_min:
        raise NoMatchingTemplateError("Requested prop_count is less than template minimum")


def _map_node(node: ScriptNode) -> DomainNode:
    return DomainNode(
        node_id=node.id,
        node_type=node.node_type,
        text=node.text,
        metadata=node.metadata_json or {},
    )


def _map_edge(edge: ScriptEdge) -> DomainEdge:
    when = edge.when_expr.expr_text if edge.when_expr is not None else None
    try:
        sel = SelectionMode(edge.selection_mode)
    except ValueError:
        sel = SelectionMode.SINGLE

    return DomainEdge(
        edge_id=edge.id,
        from_node_id=edge.from_node_id,
        to_node_id=edge.to_node_id,
        when=when,
        priority=edge.priority,
        order_index=edge.order_index,
        weight=edge.weight,
        selection_mode=sel,
    )


async def _find_pool(session: AsyncSession, *, template_id: str, kind: str) -> ResourcePool:
    from sqlalchemy import and_, select

    # Prefer template-specific pools.
    res = await session.execute(
        select(ResourcePool)
        .where(and_(ResourcePool.kind == kind, ResourcePool.is_active.is_(True), ResourcePool.template_id == template_id))
        .order_by(ResourcePool.key.asc())
    )
    pool = res.scalars().first()
    if pool is not None:
        return pool

    # Fallback to global pools.
    res = await session.execute(
        select(ResourcePool)
        .where(and_(ResourcePool.kind == kind, ResourcePool.is_active.is_(True), ResourcePool.template_id.is_(None)))
        .order_by(ResourcePool.key.asc())
    )
    pool = res.scalars().first()
    if pool is None:
        raise NoMatchingTemplateError(f"No resource pool found for kind={kind!r}")
    return pool


def _is_item_available(expr_text: str | None, state: State) -> bool:
    if expr_text is None:
        return True
    return evaluate(expr_text, state=state)


def _weighted_sample_unique(items: list[tuple[object, float]], k: int, rng) -> list[object]:  # noqa: ANN001
    """Weighted sample without replacement.

    `items` is a list of (item, weight). Items with non-positive weight are ignored.
    """

    population = [(obj, float(w)) for obj, w in items if float(w) > 0]
    selected: list[object] = []

    for _ in range(min(k, len(population))):
        total = sum(w for _, w in population)
        roll = rng.random() * total
        acc = 0.0
        for idx, (obj, w) in enumerate(population):
            acc += w
            if roll <= acc:
                selected.append(obj)
                population.pop(idx)
                break

    return selected


async def _bind_characters(
    session: AsyncSession,
    pool_repo: PoolRepository,
    template_id: str,
    request: GenerationRequest,
    state: State,
    rng,
) -> list[CharacterBinding]:
    template_repo = TemplateRepository(session)
    role_reqs = await template_repo.list_role_requirements(template_id)
    required = sum(r.count_min for r in role_reqs)
    if required == 0:
        return []

    pool = await _find_pool(session, template_id=template_id, kind="character")
    items = await pool_repo.list_character_items(pool.id)

    candidates: list[tuple[CharacterPoolItem, float]] = []
    for item in items:
        expr_text = item.condition_expr.expr_text if item.condition_expr is not None else None
        if not _is_item_available(expr_text, state):
            continue
        if not item.resource.is_active:
            continue
        effective_weight = float(item.weight) * float(item.resource.base_weight)
        candidates.append((item, effective_weight))

    picked_items = _weighted_sample_unique(candidates, k=required, rng=rng)
    if len(picked_items) < required:
        raise NoMatchingTemplateError("Not enough available character candidates to satisfy template")

    bindings: list[CharacterBinding] = []
    # Assign in stable role order.
    role_reqs_sorted = sorted(role_reqs, key=lambda r: (r.order_index, r.role_type))
    item_idx = 0
    for req in role_reqs_sorted:
        for _ in range(req.count_min):
            item = picked_items[item_idx]
            item_idx += 1
            bindings.append(
                CharacterBinding(
                    role_type=req.role_type,
                    character_id=item.resource.id,
                    character_slug=item.resource.slug,
                    display_name=item.resource.display_name,
                )
            )
    return bindings


async def _bind_locations(
    session: AsyncSession,
    pool_repo: PoolRepository,
    template_id: str,
    request: GenerationRequest,
    state: State,
    rng,
) -> list[LocationBinding]:
    pool = await _find_pool(session, template_id=template_id, kind="location")
    items = await pool_repo.list_location_items(pool.id)

    desired = request.location_count
    if desired <= 0:
        return []

    candidates: list[tuple[LocationPoolItem, float]] = []
    for item in items:
        expr_text = item.condition_expr.expr_text if item.condition_expr is not None else None
        if not _is_item_available(expr_text, state):
            continue
        if not item.resource.is_active:
            continue
        effective_weight = float(item.weight) * float(item.resource.base_weight)
        candidates.append((item, effective_weight))

    picked_items = _weighted_sample_unique(candidates, k=desired, rng=rng)
    if len(picked_items) < desired:
        raise NoMatchingTemplateError("Not enough available location candidates")

    return [
        LocationBinding(
            location_id=item.resource.id,
            location_slug=item.resource.slug,
            display_name=item.resource.display_name,
        )
        for item in picked_items
    ]


async def _bind_props(
    session: AsyncSession,
    pool_repo: PoolRepository,
    template_id: str,
    request: GenerationRequest,
    state: State,
    rng,
) -> list[PropBinding]:
    desired = request.prop_count
    if desired <= 0:
        return []

    pool = await _find_pool(session, template_id=template_id, kind="prop")
    items = await pool_repo.list_prop_items(pool.id)

    candidates: list[tuple[PropPoolItem, float]] = []
    for item in items:
        expr_text = item.condition_expr.expr_text if item.condition_expr is not None else None
        if not _is_item_available(expr_text, state):
            continue
        if not item.resource.is_active:
            continue
        effective_weight = float(item.weight) * float(item.resource.base_weight)
        candidates.append((item, effective_weight))

    picked_items = _weighted_sample_unique(candidates, k=desired, rng=rng)
    if len(picked_items) < desired:
        raise NoMatchingTemplateError("Not enough available prop candidates")

    return [
        PropBinding(
            prop_id=item.resource.id,
            prop_slug=item.resource.slug,
            display_name=item.resource.display_name,
        )
        for item in picked_items
    ]
