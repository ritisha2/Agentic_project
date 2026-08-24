from typing import TypedDict, List, Dict, Any, Optional


class DiagnosticState(TypedDict):
    user_query: str
    asset_id: str
    kb_path: str
    manifest: Optional[Dict[str, Any]]
    telemetry_metrics: List[Dict[str, Any]]
    rule_evaluations: List[Dict[str, Any]]
    topology_findings: List[Dict[str, Any]]
    rag_citations: List[Dict[str, Any]]
    diagnostic_result: Optional[Dict[str, Any]]
    audit_trail: List[str]
    error: Optional[str]
