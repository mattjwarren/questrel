# Questrel — Implementation Status

Date started: 2026-01-13

This document tracks progress against the plan in planning/initial_plan.md.

## Status Legend
- Not started
- In progress
- Blocked
- Done

## Current Summary
- Overall: In progress
- Current phase: Phase C
- Next action: Expand generator constraints/tags

## Phase A — DSL + Branching Runtime

Status: Done

Checklist:
- [x] Create core Pydantic dataclass models (State, Node, Edge, GeneratedPlay)
- [x] Implement SelectionMode enum (SINGLE/MULTI)
- [x] Implement DSL parse (`ast.parse`, mode=eval)
- [x] Implement DSL AST validation (allowlist + limits)
- [x] Implement DSL evaluator (missing flags -> None)
- [x] Implement branching resolution:
  - [x] filter by condition
  - [x] sort by priority desc, order asc
  - [x] select MULTI edges
  - [x] select at most one SINGLE edge (FIRST/RANDOM/WEIGHTED)
  - [x] return [] if no valid edges
- [x] Deterministic RNG utilities
- [x] Unit tests for DSL + branching determinism

Notes / Decisions:
- DSL permanently uses `state.flags["x"]` with str-only keys
- Expression limits: len<=8192, nodes<=1024, depth<=48

## Phase B — Storage (SQLite-first, Postgres-ready)

Status: Done

Checklist:
- [x] Set up SQLAlchemy 2.0 async engine/session
- [x] SQLite connect pragmas: foreign_keys=ON (+ optional WAL)
- [x] Implement JSON-as-TEXT TypeDecorator
- [x] Implement ORM schema:
  - [x] templates + requirements
  - [x] script nodes/edges
  - [x] condition expressions
  - [x] resource catalogs (characters/locations/props)
  - [x] tags + join tables
  - [x] pools + pool items (with condition_expr)
- [x] Implement repositories:
  - [x] TemplateRepository
  - [x] GraphRepository
  - [x] CatalogRepository
  - [x] PoolRepository
  - [x] ConditionRepository

Notes:
- Phase B is scaffolded with SQLAlchemy async models, repositories, and Alembic env.
- Added initial Alembic migration and async storage tests.

Notes:
- Constraints/metadata/specs are JSON stored as TEXT behind a stable Python type façade

## Phase C — End-to-End Generation API

Status: Done

Checklist:
- [x] Define GenerationRequest model
- [x] Implement template selection by request constraints
- [x] Implement resource binding pipeline
- [x] Implement minimal constraint solver integration
- [x] Generate a GeneratedPlay output
- [x] Add JSON rendering convenience methods
- [x] Provide minimal example dataset + example generator usage
- [x] End-to-end tests

## Open Questions (Track Here)
- None currently (all key MVP decisions locked in)

## Change Log
- 2026-01-13: Created initial plan + status tracker
- 2026-01-13: Implemented Phase A/B/C MVP with tests
