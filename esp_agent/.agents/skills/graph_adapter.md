# Skill: Graph Adapter

## Purpose
Queries graph databases (Neo4j or local topology JSON) to fetch asset subsystem hierarchies, component dependencies, and symptom cause-effect paths.

## Inputs
- `asset_id`: String identifier for target equipment.
- `query_type`: `get_components`, `get_failure_modes`, or `trace_cause_effect`.

## Outputs
- List of `ComponentNode` models and structured cause-effect relationships.
