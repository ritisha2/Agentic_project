from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class TelemetryPoint(BaseModel):
    asset_id: str
    timestamp: datetime
    scenario: Optional[str] = None
    state: Optional[str] = None
    values: dict[str, float | int | None] = Field(default_factory=dict)
    voltage_imbalance_pct: Optional[float] = None
    current_imbalance_pct: Optional[float] = None
