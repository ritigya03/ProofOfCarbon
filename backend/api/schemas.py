from pydantic import BaseModel, Field
from typing import Optional


class AnalyzeResponse(BaseModel):

    # ── Project identity (extracted by ProjectAnalysisAgent) ──────────────────
    project_name: Optional[str] = "Unknown"
    company_name: Optional[str] = "Unknown"
    state: Optional[str] = None
    forest_type: Optional[str] = None

    # ── Spatial metrics (from geospatial tools — never from LLM) ─────────────
    claimed_hectares: float
    verified_hectares: float
    overlap_percent: float
    protected_area_overlap_ha: float = 0.0

    # ── Satellite fields (from SatelliteEvidenceAgent) ────────────────────────
    ndvi_current_mean: Optional[float] = None
    ndvi_historical_mean: Optional[float] = None
    ndvi_trend: Optional[str] = None  # INCREASING / STABLE / DECREASING
    ndvi_anomaly_score: Optional[float] = None
    vegetation_class: Optional[str] = None  # DENSE_FOREST / MODERATE_FOREST / etc.
    satellite_risk_level: Optional[str] = None
    satellite_trust_modifier: Optional[float] = None
    satellite_flags: list[str] = []
    satellite_summary: Optional[str] = None

    # ── Fraud detection fields (from FraudDetectionAgent) ────────────────────
    anomaly_score: Optional[float] = None
    fraud_risk_level: Optional[str] = None
    fraud_patterns: Optional[dict] = None
    fraud_flags: list[str] = []
    fraud_summary: Optional[str] = None

    # ── Final verdict (from VerifierAgent) ───────────────────────────────────
    final_verdict: Optional[str] = (
        None  # VERIFIED / CONDITIONALLY_VERIFIED / REQUIRES_REVIEW / REJECTED
    )
    final_trust_score: Optional[float] = None
    final_risk_level: Optional[str] = None
    confidence: Optional[str] = None  # HIGH / MEDIUM / LOW
    key_findings: list[str] = []
    recommendation: Optional[str] = None
    verification_summary: Optional[str] = None

    # ── Canonical verdict fields (always populated — fall back to Stage 1 if later stages fail) ──
    risk_level: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    trust_score: float = Field(..., ge=0, le=100)
    summary: str

    # ── All accumulated flags from all stages ─────────────────────────────────
    all_flags: list[str] = []
    analysis_flags: list[str] = []
    red_flags: list[str] = []


class HealthResponse(BaseModel):
    status: str
    agent_ready: bool
