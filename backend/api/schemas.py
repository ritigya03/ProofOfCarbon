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

    # Verdict — spatial
    risk_level: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    trust_score: float = Field(..., ge=0, le=100)

    # Spatial detail
    all_flags: list[str] = []
    analysis_flags: list[str] = []
    red_flags: list[str] = []
    summary: str

    # ── Satellite Evidence (SatelliteEvidenceAgent) ───────────────────────────
    ndvi_current_mean: Optional[float] = None
    ndvi_historical_mean: Optional[float] = None
    ndvi_trend: Optional[str] = None          # INCREASING | STABLE | DECREASING
    ndvi_anomaly_score: Optional[float] = None
    ndvi_pixel_count: Optional[int] = None
    ndvi_data_source: Optional[str] = None    # MODIS_MOD13Q1 | MOCK

    vegetation_class: Optional[str] = None   # DENSE_FOREST | MODERATE_FOREST | SPARSE_VEGETATION | DEGRADED | BARE_GROUND
    satellite_risk_level: Optional[str] = None
    satellite_trust_modifier: Optional[int] = None
    satellite_flags: list[str] = []
    satellite_summary: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    agent_ready: bool
