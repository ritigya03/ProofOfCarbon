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

    # ── Bounding box — used by the frontend satellite map ─────────────────────
    bbox: Optional[dict] = None           # {min_lon, min_lat, max_lon, max_lat}

    # ── Stage-specific scores (preserved before Verifier overwrites trust_score) ─
    spatial_trust_score: Optional[float] = None   # ProjectAnalysisAgent's own score

    # ── Reference land-cover GeoJSON (fetched from OSM/Overpass) ─────────────
    # Contains scrub, forest, plantation, orchard polygons overlapping the bbox.
    # Passed to SatelliteMap for display as coloured overlays.
    reference_geojson: Optional[dict] = None

    # ── Area mismatch (text description vs KMZ measurement) ──────────────────
    text_claimed_ha: Optional[float] = None    # ha extracted from company text
    area_mismatch_pct: Optional[float] = None  # % difference vs KMZ area

    # ── Satellite source label (shown in the NDVI card badge) ────────────────
    ndvi_data_source: Optional[str] = None

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

    # ── Historical Baseline fields (from HistoricalBaselineAgent) ────────────
    additionality_verdict: Optional[str] = None    # STRONG / MODERATE / WEAK / NEGLIGIBLE
    baseline_risk_level: Optional[str] = None      # LOW / MEDIUM / HIGH / CRITICAL
    baseline_trust_modifier: Optional[float] = None
    additionality_score: Optional[float] = None
    deforestation_pressure: Optional[str] = None   # LOW / MEDIUM / HIGH / CRITICAL
    counterfactual_loss_ha: Optional[float] = None
    carbon_at_risk_tonnes_co2e: Optional[float] = None
    counterfactual_assessment: Optional[str] = None
    permanence_assessment: Optional[str] = None
    additionality_flags: list[str] = []
    baseline_summary: Optional[str] = None

    # ── Fraud detection fields (from FraudDetectionAgent) ────────────────────
    anomaly_score: Optional[float] = None
    fraud_risk_level: Optional[str] = None
    fraud_patterns: Optional[dict] = None
    fraud_flags: list[str] = []
    fraud_summary: Optional[str] = None

    # ── ML model predictions (from FraudDetectionAgent ML layer) ──────────
    ml_anomaly_score: Optional[float] = None
    ml_fraud_risk_level: Optional[str] = None
    ml_verdict: Optional[str] = None
    ml_confidence: Optional[float] = None
    ml_class_probabilities: Optional[dict] = None

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
