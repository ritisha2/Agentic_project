# Agent Specifications - ESP Diagnostic Agent

This document defines the agent architecture and custom skills for the Knowledge-Base-Agnostic ESP Diagnostic Agent system.

## Domain Independence
The core agent logic communicates solely via Pydantic Canonical Schemas (`Asset`, `TelemetryMetric`, `ComponentNode`, `DiagnosticResult`). All domain-specific terms (such as `motor_temperature`, `intake_pressure`) are localized in `mapping_config.json` and handled at the adapter layer.
