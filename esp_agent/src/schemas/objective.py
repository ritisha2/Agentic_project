"""
Pydantic Schemas for Objective Definitions & Objective Registry
Grounded in PHASE_4_Objective_Layer_Implementation_Plan_ESP_APM.docx §20, §27
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ObjectiveSafetyPolicy(BaseModel):
    advisory_only: bool = Field(default=True, description="Strict safety flag prohibiting autonomous control")
    max_frequency_change_hz: Optional[float] = Field(default=None, description="Max allowed frequency adjustment suggestion")
    forbidden_actions: List[str] = Field(default_factory=list, description="Explicitly prohibited operational recommendations")


class ObjectiveDefinition(BaseModel):
    objective_id: str = Field(description="Unique Level-2 operational objective identifier, e.g. OP02_PRODUCTION_DECLINE_RCA")
    version: str = Field(default="1.0", description="Schema version of objective definition")
    title: str = Field(default="", description="Human-readable title of objective")
    description: str = Field(default="", description="Detailed description of objective scope")
    
    strategic_objectives: List[str] = Field(default_factory=list, description="Level-1 Strategic Objective mappings (e.g. ['O1', 'O5'])")
    intent_classes: List[str] = Field(default_factory=list, description="Intent classification keywords / phrases")
    
    required_asset_context: List[str] = Field(default_factory=list, description="Required asset context attributes")
    required_signals: List[str] = Field(default_factory=list, description="Required telemetry sensor signal tags")
    required_evidence: List[str] = Field(default_factory=list, description="Required evidence types: telemetry, history, events, KB, models")
    required_tools: List[str] = Field(default_factory=list, description="Deterministic engineering calculation tools & services")
    allowed_specialists: List[str] = Field(default_factory=list, description="Specialist reasoning modules allowed")
    
    safety: ObjectiveSafetyPolicy = Field(default_factory=ObjectiveSafetyPolicy, description="Operational safety boundaries")
    output_format: str = Field(default="advisory_v1", description="Target advisory response format")
    
    success_criteria: List[str] = Field(default_factory=list, description="Machine-verifiable conditions for successful execution")
    verification_steps: List[str] = Field(default_factory=list, description="Human operator verification checks")
