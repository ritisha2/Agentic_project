# Workflow: Diagnostic Workflow

- Step 1: Load knowledge base manifest and mapping configuration
- Step 2: Validate knowledge base capabilities
- Step 3: Initialize adapters (telemetry, graph, rag, rules)
- Step 4: Receive user query via CLI or REST API
- Step 5: Parse query to identify asset and intent
- Step 6: Execute diagnostic workflow via LangGraph
- Step 7: Return DiagnosticResult
- Step 8: Log execution to audit trail
