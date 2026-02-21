from pydantic import BaseModel, Field
from typing import Optional


class AnalyzeResponse(BaseModel):
    # Identity
    project_name: Optional[str] = "Unknown"
    company_name: Optional[str] = "Unknown"
    state: Optional[str] = None
    forest_type: Optional[str] = None

    # Core spatial metrics (always populated from geospatial tools, not LLM)
    claimed_hectares: float
    verified_hectares: float
    overlap_percent: float
    protected_area_overlap_ha: float = 0.0

    # Verdict
    risk_level: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    trust_score: float = Field(..., ge=0, le=100)

    # Detail
    all_flags: list[str] = []
    analysis_flags: list[str] = []
    red_flags: list[str] = []
    summary: str


class HealthResponse(BaseModel):
    status: str
    agent_ready: bool
