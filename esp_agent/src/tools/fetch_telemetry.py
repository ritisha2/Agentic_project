from typing import List
from src.adapters.telemetry import TelemetryAdapter
from src.schemas.canonical import TelemetryMetric


def fetch_telemetry_tool(telemetry_adapter: TelemetryAdapter, asset_id: str) -> List[TelemetryMetric]:
    """Tool function to fetch and translate telemetry for a given asset."""
    return telemetry_adapter.load_latest_telemetry(asset_id=asset_id)
