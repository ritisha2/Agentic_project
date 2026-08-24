import json
import os
from typing import List, Dict, Any, Optional
from src.schemas.canonical import ComponentNode


class GraphAdapter:
    """Universal Graph Adapter supporting Neo4j with local JSON fallback for asset topology and cause-effect relationships."""

    def __init__(self, graph_json_path: Optional[str] = None, neo4j_uri: Optional[str] = None):
        self.graph_json_path = graph_json_path
        self.neo4j_uri = neo4j_uri
        self._graph_data: Dict[str, Any] = {}
        if graph_json_path and os.path.exists(graph_json_path):
            with open(graph_json_path, "r", encoding="utf-8") as f:
                self._graph_data = json.load(f)

    @classmethod
    def from_file(cls, graph_json_path: str) -> "GraphAdapter":
        return cls(graph_json_path=graph_json_path)

    def get_components(self, asset_id: str) -> List[ComponentNode]:
        """Returns component nodes belonging to the asset."""
        if not self._graph_data:
            return []

        nodes: List[ComponentNode] = []
        raw_components = self._graph_data.get("components", [])
        raw_subsystems = self._graph_data.get("subsystems", [])

        # Build component objects
        for comp in raw_components:
            comp_name = comp if isinstance(comp, str) else comp.get("name")
            parent = comp.get("subsystem") if isinstance(comp, dict) else "Motor Section"
            metrics = comp.get("metrics", []) if isinstance(comp, dict) else []
            nodes.append(ComponentNode(
                component_name=comp_name,
                parent_component=parent,
                monitored_metrics=metrics
            ))

        if not nodes and raw_subsystems:
            for sub in raw_subsystems:
                sub_name = sub if isinstance(sub, str) else sub.get("name")
                nodes.append(ComponentNode(
                    component_name=sub_name,
                    parent_component=asset_id,
                    monitored_metrics=[]
                ))
        return nodes

    def get_failure_modes(self, target: str) -> List[Dict[str, Any]]:
        """Returns failure modes associated with an asset, subsystem, component, or symptom."""
        if not self._graph_data:
            return []

        raw_fm = self._graph_data.get("failure_modes", [])
        relationships = self._graph_data.get("relationships", [])

        results = []
        target_lower = target.lower()

        for rel in relationships:
            rel_type = rel.get("type", "")
            source = rel.get("source", "").lower()
            target_node = rel.get("target", "").lower()

            if target_lower in source or target_lower in target_node:
                results.append(rel)

        # Fallback to direct failure modes if no matching relationships
        if not results and raw_fm:
            for fm in raw_fm:
                fm_name = fm if isinstance(fm, str) else fm.get("name")
                results.append({
                    "source": target,
                    "type": "can_fail_with",
                    "target": fm_name
                })

        return results

    def trace_cause_effect(self, symptom_or_metric: str) -> List[Dict[str, Any]]:
        """Traces symptoms or abnormal metrics back to root cause failure modes and components."""
        if not self._graph_data:
            return []

        relationships = self._graph_data.get("relationships", [])
        matched_traces = []
        key_lower = symptom_or_metric.lower()

        for rel in relationships:
            src = rel.get("source", "")
            tgt = rel.get("target", "")
            rel_type = rel.get("type", "")

            if key_lower in src.lower() or key_lower in tgt.lower():
                matched_traces.append({
                    "symptom_or_metric": symptom_or_metric,
                    "relationship": rel_type,
                    "connected_node": tgt if key_lower in src.lower() else src,
                    "full_rule": f"{src} -> {rel_type} -> {tgt}"
                })

        return matched_traces
