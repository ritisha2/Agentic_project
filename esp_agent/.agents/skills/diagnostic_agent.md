# Skill: Diagnostic Agent

## Purpose
Orchestrates the diagnostic workflow using a LangGraph state machine to produce a structured `DiagnosticResult`.

## Execution Workflow
1. Parse user query & validate asset against manifest.
2. Call `telemetry_adapter` to get canonical metrics.
3. Call `rule_adapter` to evaluate deterministic threshold rules.
4. Call `graph_adapter` to trace cause-effect relationships for anomalies.
5. Call `rag_adapter` to search troubleshooting documentation.
6. Synthesize evidence into canonical `DiagnosticResult`.
