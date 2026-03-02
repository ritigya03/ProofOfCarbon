"""
satellite_evidence.py — Validates carbon credit claims against satellite NDVI data.

Data source: NASA MODIS Terra (MOD13Q1) via Google Earth Engine Python API.
Fallback:    Deterministic mock (no credentials needed).
"""

import logging
from agents.base_agent import BaseAgent
from tools.satellite import fetch_ndvi_for_bbox

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a remote sensing expert and carbon credit auditor specialising in Indian forestry.

You will receive:
1. NASA MODIS satellite NDVI data for the project's bounding box (both current and historical)
2. The company's own text description of their project
3. Key findings from the spatial analysis (overlap %, claimed area, risk level)

Your job is to assess whether the satellite evidence SUPPORTS or CONTRADICTS the carbon credit claim.

NDVI interpretation guide:
- PROJECT TYPE = REDD+:
    - NDVI > 0.60 = Dense forest — strongly supports claims.
    - NDVI 0.40-0.60 = Moderate forest — partially supports claims.
    - NDVI < 0.40 = RED FLAG / SPARSE — unlikely to be a valid REDD+ project.
- PROJECT TYPE = ARR:
    - NDVI 0.30-0.50 = Normal for young plantation / restoration — supports claims.
    - NDVI < 0.20 = Very sparse — caution, but plausible for early-stage ARR.
    - NDVI > 0.60 = Already dense forest — suspicion (why reforestation if already forest?).

Trend interpretation:
- INCREASING (>10% gain): STRONG SUPPORT for ARR (new growth). Positive for REDD+.
- STABLE (±10%): Neutral/Support for REDD+ (conservation). Neutral for ARR.
- DECREASING (>10% loss): CRITICAL RED FLAG for all types (deforestation).

Return ONLY a valid JSON object with these exact fields:
{
  "vegetation_class": "<one of: DENSE_FOREST, MODERATE_FOREST, SPARSE_VEGETATION, DEGRADED, BARE_GROUND>",
  "satellite_risk_level": "<one of: LOW, MEDIUM, HIGH, CRITICAL>",
  "satellite_trust_modifier": <integer, -30 to +10>,
  "satellite_flags": ["<flag1>", "<flag2>"],
  "satellite_summary": "<2-3 sentence plain English assessment of what the satellite data shows in the context of the project type>"
}

Scoring satellite_trust_modifier:
- ARR + Increasing Trend: +5 to +10
- ARR + NDVI 0.3-0.5 (Stage 1-2): 0 to +5
- REDD+ + Dense Forest (>0.6) + Stable: +5 to +10
- REDD+ + NDVI < 0.4: -20 to -10
- ANY + Decreasing TREND: -30 to -15
- ARR + Already High NDVI (>0.7): -10 (Baseline inflation suspicion)
"""


class SatelliteEvidenceAgent(BaseAgent):
    """
    Fetches satellite NDVI data for the project bbox and uses an LLM
    to interpret whether the evidence supports the carbon credit claim.
    """

    def __init__(self):
        super().__init__(
            name="SatelliteEvidenceAgent",
            system_prompt=SYSTEM_PROMPT,
        )

    def run(
        self,
        bbox: dict,
        company_text_claim: str = "",
        project_analysis_result: dict | None = None,
    ) -> dict:
        """
        Run satellite evidence analysis.

        Args:
            bbox: {"min_lon", "min_lat", "max_lon", "max_lat"} from KMZ
            company_text_claim: raw text description from the company
            project_analysis_result: dict from ProjectAnalysisAgent (optional context)

        Returns:
            dict with satellite evidence fields merged with raw NDVI data
        """
        logger.info(f"[SatelliteEvidenceAgent] Fetching NDVI for bbox: {bbox}")

        # ── Step 1: Fetch satellite data ──────────────────────────────────────
        ndvi_data = fetch_ndvi_for_bbox(bbox)

        logger.info(
            f"[SatelliteEvidenceAgent] NDVI — current={ndvi_data['ndvi_current_mean']}, "
            f"historical={ndvi_data['ndvi_historical_mean']}, "
            f"trend={ndvi_data['ndvi_trend']}, source={ndvi_data['data_source']}"
        )

        # ── Step 2: Build LLM context ─────────────────────────────────────────
        geo_context = {}
        if project_analysis_result:
            geo_context = {
                "project_type":              project_analysis_result.get("project_type"),
                "overlap_percent":           project_analysis_result.get("overlap_percent"),
                "claimed_hectares":          project_analysis_result.get("claimed_hectares"),
                "verified_hectares":         project_analysis_result.get("verified_hectares"),
                "spatial_risk_level":        project_analysis_result.get("risk_level"),
                "protected_area_overlap_ha": project_analysis_result.get("protected_area_overlap_ha"),
                "spatial_flags":             project_analysis_result.get("all_flags", []),
            }

        prompt = self._build_prompt(
            company_text_claim=company_text_claim or "No text claim provided",
            satellite_ndvi_data=ndvi_data,
            spatial_analysis_context=geo_context,
        )

        # ── Step 3: LLM reasoning ─────────────────────────────────────────────
        raw     = self._call_llm(prompt)
        result  = self._parse_json(raw)

        # ── Step 4: Merge raw NDVI numbers in (don't let LLM change them) ────
        result["ndvi_current_mean"]    = ndvi_data["ndvi_current_mean"]
        result["ndvi_historical_mean"] = ndvi_data["ndvi_historical_mean"]
        result["ndvi_trend"]           = ndvi_data["ndvi_trend"]
        result["ndvi_anomaly_score"]   = ndvi_data["ndvi_anomaly_score"]
        result["ndvi_pixel_count"]     = ndvi_data["pixel_count"]
        result["ndvi_data_source"]     = ndvi_data["data_source"]

        # Merge tool-generated flags with LLM flags (avoid duplicates)
        llm_flags = result.get("satellite_flags", [])
        all_sat_flags = ndvi_data["flags"] + [
            f for f in llm_flags if f not in ndvi_data["flags"]
        ]
        result["satellite_flags"] = all_sat_flags

        logger.info(
            f"[SatelliteEvidenceAgent] Done — "
            f"vegetation_class={result.get('vegetation_class')}, "
            f"satellite_risk={result.get('satellite_risk_level')}, "
            f"trust_modifier={result.get('satellite_trust_modifier')}"
        )

        return result
