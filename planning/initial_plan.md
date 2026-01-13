# Questrel — Initial Plan (MVP + Evolution Path)

Date: 2026-01-13

## 1. Vision

Questrel is a Python library that generates a structured, game-consumable “play/quest” from a database of play templates, branching scripts, and resource pools (characters, locations, props). A game can request constraints like:

- “Generate a play that fits 4 locations and ≤3 characters.”

Questrel selects a suitable template and fills it with randomized (or weighted-random) concrete resources while preserving story consistency via constraints. It outputs a `GeneratedPlay` either as a Pydantic model or JSON.

## 2. Key Requirements (Decisions Locked In)

### 2.1 Runtime + output
- Library language: Python
- Dependency manager: `uv`
- Execution: **asynchronous** (async-first API)
- Models: **Pydantic dataclasses** (Pydantic v2)
- Output: return Pydantic dataclasses OR render to JSON

### 2.2 Branching story graph
- Scripts support branching based on conditions.
- Branch conditions can be author-defined and depend on:
  - `state.flags` (mixed scalar types)
  - previous decisions, inventory/props, etc. (represented in `state.flags` for MVP)
- Conflict resolution when multiple edges are valid:
  - use **priority** + **random/weighted choice**
  - deterministic ordering when not random
  - support returning **multiple** valid branches (“multi-edge events”)

### 2.3 Condition language
- Use an author-friendly **string expression DSL**.
- DSL is evaluated by a **safe interpreter** (parse + validate AST; never `eval`/`compile`).
- DSL access style (MVP and permanently): `state.flags["x"]`
- Missing keys in `state.flags` must evaluate as **`None`**, not an error.
- Initial expression limits:
  - max length: `8192` chars
  - max AST nodes: `1024`
  - max AST depth: `48`

### 2.4 Database
- Initial backend: **SQLite**
- Must be written to allow future switch to **Postgres** with minimal churn.
- Use **SQLAlchemy 2.0 async**.
- Store constraints/metadata/specs as **JSON-as-TEXT behind a stable Python type façade** so generator/repo code does not change when migrating to Postgres JSONB.

### 2.5 Resource pools
- Include **full resource pools immediately**:
  - character resources
  - location resources
  - prop resources
- Must support:
  - pure random
  - weighted random
  - conditional availability (pool item uses the same DSL as edges)
  - constraints for story consistency

## 3. Terminology

- **Template**: reusable blueprint for a play/quest.
- **Graph / Script**: node/edge representation of narration/dialogue/scene structure.
- **Node**: a piece of script (narration, scene description, dialogue beat, choice prompt, etc.).
- **Edge**: transition between nodes, guarded by a condition expression.
- **Resource catalog**: all available characters/locations/props.
- **Pool**: a curated subset of the catalog; contains weighted items.
- **Binding**: a concrete chosen resource assigned to a role/location/prop requirement.

## 4. Package Layout (Target)

```
src/questrel/
  __init__.py
  api.py

  models/
    enums.py
    state.py
    story.py
    generated.py

  dsl/
    parse.py
    validate.py
    eval.py
    errors.py

  random/
    deterministic.py

  runtime/
    branching.py

  resources/
    spec.py
    solver.py

  storage/
    engine.py
    types.py
    models.py
    repositories/
      template_repo.py
      graph_repo.py
      pool_repo.py
      catalog_repo.py
      condition_repo.py
    migrations/
      ... (alembic)

  seed/
    minimal_seed.py
```

## 5. Public API (Async)

### 5.1 Core function(s)
- `generate_play(request: GenerationRequest, storage: Storage, *, seed: int | None = None) -> GeneratedPlay`

### 5.2 Serialization
- `GeneratedPlay` supports:
  - `model_dump()` for dict
  - `model_dump_json()` for JSON

## 6. Pydantic Models (MVP)

### 6.1 State
- `State.flags: dict[str, bool | int | float | str | None]`
- Missing key behavior:
  - `state.flags["missing"]` in DSL evaluates to `None`

### 6.2 Graph models
- `ScriptNode`
  - `node_id: str`
  - `node_type: str` (e.g., `scene`, `narration`, `dialogue`, `choice`, `event`)
  - `text: str | None`
  - `metadata: dict` (JSON-as-text in DB, dict in model)

- `ScriptEdge`
  - `edge_id: str` (must be unique; multiple edges between same nodes are allowed)
  - `from_node_id: str`
  - `to_node_id: str`
  - `when: str | None` (DSL expression; `None` means always true)
  - `priority: int = 0`
  - `order_index: int = 0` (preserve author order)
  - `weight: float = 1.0`
  - `selection_mode: SelectionMode` (stored per edge)

### 6.3 SelectionMode
Stored per edge/pool item.

Recommended MVP enum:
- `SINGLE`: edge/item participates in “choose-one” (at most 1 selected in that decision step)
- `MULTI`: edge/item participates in “choose-many” (can return multiple)

Note: at runtime, the resolver determines the result set for a given node/event by filtering/sorting and then applying selection rules. `selection_mode` is read from each edge/item.

### 6.4 GeneratedPlay
- `generated_id: str`
- `template_id: str`
- `seed: int`
- `nodes: list[ScriptNode]`
- `edges: list[ScriptEdge]`
- `bindings`:
  - `characters: list[CharacterBinding]`
  - `locations: list[LocationBinding]`
  - `props: list[PropBinding]`

## 7. Condition DSL (Safe, Author-Friendly)

### 7.1 Author syntax (MVP)
- Only access flags via:
  - `state.flags["flag_name"]`
- Allowed operators (MVP):
  - boolean: `and`, `or`, `not`
  - comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
  - membership: `in`, `not in` (right operand should be literal list/tuple)
- Literals:
  - `None`, `True`, `False`
  - numbers, strings
  - list/tuple literals for membership checks

Examples:
- `state.flags["met_mayor"] == True and state.flags["reputation"] >= 10`
- `state.flags["key"] != None`
- `state.flags["faction"] in ["mages", "thieves"]`

### 7.2 Safety constraints
- Parse with `ast.parse(expr, mode="eval")`.
- Validate AST using a strict allowlist.
- Never `eval()` or compile Python code.
- Disallow function calls, comprehensions, attribute access, imports, etc.

### 7.3 Missing key semantics
- Accessing a missing key returns `None`.
- Comparisons with `None` follow Python semantics.

### 7.4 Limits
- `max_len=8192`
- `max_nodes=1024`
- `max_depth=48`

## 8. Branch Resolution Semantics

### 8.1 Deterministic ordering
After filtering valid edges, sort edges by:
1) `priority` descending
2) `order_index` ascending
3) `edge_id` ascending (tie-break for stability)

### 8.2 Filtering
- Evaluate `edge.when` using the DSL.
- If `edge.when is None`, treat as always true.

### 8.3 Selection rules
Because `selection_mode` is per edge, a node’s outgoing set may contain a mix.

Recommended MVP behavior per decision step:
1) Filter valid edges.
2) If none valid: return `[]`.
3) Identify highest-priority tier: `p_max = max(priority)`.
4) Keep only edges where `priority == p_max`.
5) From this tier:
   - include all `MULTI` edges (in sorted order)
   - among `SINGLE` edges, choose at most one using strategy:
     - `FIRST`: first `SINGLE` edge in sorted order
     - `RANDOM`: uniform over `SINGLE` edges
     - `WEIGHTED`: weighted over `SINGLE` edges by `weight`

Notes:
- The resolver should accept a strategy parameter (or be configured at node/template level later).
- Even if `MULTI` edges exist, the system may still also choose one `SINGLE` edge in the same step if desired; MVP should define this clearly (default: return MULTI edges + at most one SINGLE edge).

## 9. Deterministic Randomness

- Use a dedicated RNG instance for generation and for each decision.
- Seed derivation must be stable and reproducible:
  - base seed from request or generated
  - derived seed for a node decision: hash of `(base_seed, template_id, node_id, decision_index)`
- Persist chosen edges/bindings in the output for replay/debug.

## 10. Resource Selection + Consistency Constraints

### 10.1 Catalogs
- Separate catalogs:
  - `character_resource`
  - `location_resource`
  - `prop_resource`

Each resource includes:
- `resource_id`, `slug`, `display_name`
- tags (normalized join tables)
- `metadata` (JSON-as-text façade)
- `base_weight`, `rarity`, `is_active`

### 10.2 Pools
- `resource_pool` plus per-kind item tables:
  - `character_pool_item`
  - `location_pool_item`
  - `prop_pool_item`

Each pool item includes:
- `weight` multiplier
- `condition_expr` (DSL; same evaluator as edges)
- metadata (JSON-as-text façade)

### 10.3 Requirements
Templates define requirements:
- roles (types + counts + tag constraints)
- number/type of locations
- number/type of props

### 10.4 Constraints (MVP)
Represent selection as variable binding with a minimal constraint set:
- `eq(a, b)`
- `neq(a, b)`
- `in(a, set)`
- `all_distinct([a,b,c])`

Approach:
- pick “most constrained first”
- backtracking if needed
- weighted candidate ordering with deterministic RNG

## 11. Storage Layer (SQLAlchemy Async)

### 11.1 Engine URLs
- SQLite file: `sqlite+aiosqlite:///./questrel.db`
- Postgres future: `postgresql+asyncpg://...`

### 11.2 SQLite pragmas
On connect:
- `PRAGMA foreign_keys=ON`
- optionally `PRAGMA journal_mode=WAL`

### 11.3 JSON-as-TEXT façade
- Store JSON payloads in TEXT in SQLite.
- Expose them as `dict` in Python using a SQLAlchemy `TypeDecorator`.
- Later migrate columns to JSONB in Postgres without changing repository/generator code.

### 11.4 Core tables (MVP)
- template:
  - `play_template`
  - requirements (roles/locations/props)
- graph:
  - `script_node`
  - `script_edge`
  - `condition_expression`
- catalogs:
  - `character_resource`, `location_resource`, `prop_resource`
  - `tag` and join tables
- pools:
  - `resource_pool` and kind-specific pool items

### 11.5 Repositories
Repositories accept an async session and provide minimal data access:
- TemplateRepository: find templates by constraints, load requirements
- GraphRepository: load nodes/edges for template
- CatalogRepository: query resources by tags/activity
- PoolRepository: load pool + candidate items
- ConditionRepository: load/dedupe expressions

Generator/service layer performs:
- DSL evaluation of conditions
- constraint solving
- weighted/random sampling

## 12. Migration to Postgres (Future)

Goal: no generator/repo rewrite.
- Keep API stable and switch DB URL.
- Run Alembic migrations to:
  - convert JSON TEXT columns to JSONB
  - add Postgres-specific indexes
  - tune constraints

## 13. Testing & Validation (Recommended)

- DSL tests:
  - allowlist rejection
  - missing key -> None
  - mixed scalar comparisons
  - limits enforcement
- Branching tests:
  - sorting
  - priority tiering
  - SINGLE/MULTI behavior
  - random/weighted determinism with seed
- Storage tests:
  - repository round-trips with SQLite
- End-to-end generate test:
  - minimal seeded DB -> GeneratedPlay output

## 14. Implementation Slices / Phases

### Phase A — DSL + Branching Runtime (No DB required)
Goal: compile the “decision engine” that will later run over DB-loaded graphs.

Deliverables:
- Pydantic models for `State`, `ScriptNode`, `ScriptEdge`, `SelectionMode`, `GeneratedPlay` (minimal)
- DSL:
  - parse/validate/eval
  - strict `state.flags["x"]` only
  - missing key -> None
  - limits enforced
- Branch resolver:
  - filter edges by DSL
  - sort by priority desc then order asc
  - support returning multi-edge outcomes
  - optional choose-one strategy for SINGLE edges (FIRST/RANDOM/WEIGHTED)
- Deterministic RNG utilities

Acceptance checks:
- Unit tests demonstrating deterministic resolution and safe DSL behavior.

### Phase B — Storage (SQLite-first, Postgres-ready)
Goal: create DB schema + repositories to load templates, graphs, and pools.

Deliverables:
- SQLAlchemy async engine/session + SQLite pragmas
- JSON-as-TEXT TypeDecorator
- ORM models:
  - templates + requirements
  - graph nodes/edges + condition expressions
  - catalogs + tags
  - pools + pool items with `condition_expr`
- Repositories providing:
  - load template + requirements
  - load graph
  - load pool candidates with tags
- Alembic migrations for schema creation

Acceptance checks:
- Can create SQLite DB, apply migrations, insert minimal seed data, and load it through repositories.

### Phase C — End-to-End Generation API + Minimal Seed
Goal: implement `generate_play()` that satisfies a request, binds resources, and returns a `GeneratedPlay`.

Deliverables:
- Generation request model:
  - max characters
  - desired locations
  - optional tags/filters
  - seed
- Template selection:
  - choose a template that can satisfy constraints
- Resource binding:
  - pick characters/locations/props from pools with weighted + conditional availability
  - run minimal constraints solver for consistency
- Output:
  - return Pydantic model
  - JSON rendering supported
- Minimal seed dataset + a small example template

Acceptance checks:
- A small test script can generate a play from a seeded SQLite DB with deterministic output from a seed.
