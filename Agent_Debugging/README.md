# Agent Debugging Tools

This directory contains standalone repositories and documentation for the multi-agent debugging ecosystem evaluated for the ESP APM platform:

```text
Agent_Debugging/
├── agdebugger_repo/      # Microsoft AGDebugger (Interactive UI, step-through, state edits)
├── agentdebugx_repo/     # AgentDebugX (Closed-loop Detect -> Attribute -> Recover -> Rerun)
├── logs/                 # Trajectory recordings & debug traces
└── README.md             # This guide
```

---

## 1. 🔍 Microsoft AGDebugger (`agdebugger_repo/`)
* **GitHub**: [github.com/microsoft/agdebugger](https://github.com/microsoft/agdebugger)
* **What it does**: Interactive multi-agent debugger with visual conversation flow, breakpointing, and in-flight state modification.
* **Key Use Cases**:
  * Step-by-step execution across supervisor and specialist nodes.
  * Pausing execution before advisory synthesis to inspect and override intermediate telemetry variables.
  * Navigating multi-agent conversational trees.

---

## 2. ⚡ AgentDebugX (`agentdebugx_repo/`)
* **GitHub**: [github.com/AgentDebugX/AgentDebugX](https://github.com/AgentDebugX/AgentDebugX)
* **What it does**: Closed-loop automated debugging framework with 4 phases:
  1. **Detect**: Automatically catch runtime anomalies and schema mismatches.
  2. **Attribute**: Pinpoint the exact failing agent, node, or tool.
  3. **Recover**: Trigger automated self-repair mechanisms (e.g. `json-repair`, physics fallbacks).
  4. **Rerun**: Validate fixes against regression test suites.
* **Key Use Cases**:
  * Continuous CI/CD automated pipeline validation.
  * Attributing LLM format errors vs. MCP tool communication failures.

---

## 🚀 Structure Status:
* Both repositories are cloned cleanly into `Agent_Debugging/`.
* No core project code in `esp_agent` or `cced_esp` was modified.
