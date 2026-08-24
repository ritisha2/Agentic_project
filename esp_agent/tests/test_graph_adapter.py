from src.adapters.graph import GraphAdapter


def test_graph_adapter_topology():
    graph_path = "knowledge_bases/esp/graph/esp_graph.json"
    adapter = GraphAdapter.from_file(graph_path)

    components = adapter.get_components("ESP-Well-001")
    assert len(components) > 0
    comp_names = [c.component_name for c in components]
    assert "Motor Bearing" in comp_names or "Motor Section" in comp_names

    failure_modes = adapter.get_failure_modes("Motor Bearing")
    assert len(failure_modes) > 0

    traces = adapter.trace_cause_effect("Excessive Vibration")
    assert len(traces) > 0
    assert any("Bearing Wear" in t["connected_node"] or "Excessive Vibration" in t["full_rule"] for t in traces)
