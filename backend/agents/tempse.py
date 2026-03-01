"""
agents/satellite_evidence.py — Validates forest cover using MODIS NDVI data via NASA APPEEARS API.

For MVP / testing: falls back to a deterministic mock based on bbox location
when NASA_APPEEARS_TOKEN is not set.

Real data path (future):
    - NASA APPEEARS API: https://appeears.earthdatacloud.nasa.gov/api/
    - Product: MOD13Q1.061 (MODIS Terra Vegetation Indices, 250m, 16-day)
    - Band: 250m_16_days_NDVI
"""

import logging
import os
import random

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a remote sensing analyst specializing in Indian forest ecosystems.

You will receive:
1. NDVI statistics computed from MODIS satellite data for a claimed forest area
2. The company's original text claim
3. The spatial analysis result from Phase 1

Your job is to assess whether the satellite vegetation data supports or contradicts the carbon credit claim.

Return ONLY valid JSON with these fields:
{
  "ndvi_mean": <float, 0-1>,
  "ndvi_min": <float, 0-1>,
  "ndvi_max": <float, 0-1>,
  "canopy_cover_estimate_pct": <float, 0-100>,
  "forest_condition": "<one of: EXCELLENT, GOOD, MODERATE, POOR, NON_FOREST>",
  "satellite_trust_modifier": <float, -30 to +20>,
  "satellite_flags": ["<flag1>", ...],
  "satellite_summary": "<2 sentence interpretation of NDVI data>"
}

NDVI thresholds for India:
- Dense forest (Western Ghats, NE India): NDVI > 0.65
- Moderately dense (Deccan, Central India): 0.45-0.65
- Open forest / dry deciduous: 0.25-0.45
- Scrub / degraded: 0.10-0.25
- Non-forest (desert, agriculture, urban): < 0.10

satellite_trust_modifier rules:
- NDVI strongly supports claim: +10 to +20
- NDVI consistent with claim: 0 to +10
- NDVI partially inconsistent: -10 to 0
- NDVI contradicts claim entirely: -20 to -30

Always note if NDVI is typical for the claimed forest type and Indian state.
"""


def _mock_ndvi(bbox: dict) -> dict:
    """
    Deterministic mock NDVI values based on bbox location.
    Uses real India geography — deserts low, Ghats/NE high.

    This runs when NASA_APPEEARS_TOKEN is not set (dev/test mode).
    """
    center_lat = (bbox["min_lat"] + bbox["max_lat"]) / 2
    center_lon = (bbox["min_lon"] + bbox["max_lon"]) / 2

    # Seed from location for determinism across test runs
    seed = int(abs(center_lat * 100) + abs(center_lon * 100))
    rng = random.Random(seed)

    # Approximate NDVI by region (real ecological knowledge)
    # Western Ghats: 11-15°N, 74-77°E → very high NDVI
    if 10 <= center_lat <= 15 and 74 <= center_lon <= 78:
        base = rng.uniform(0.62, 0.82)   # Dense evergreen

    # Northeast India: 22-28°N, 90-97°E → high NDVI
    elif 22 <= center_lat <= 28 and 90 <= center_lon <= 97:
        base = rng.uniform(0.58, 0.78)

    # Central India (MP, Chhattisgarh): 18-24°N, 78-84°E → moderate
    elif 18 <= center_lat <= 24 and 78 <= center_lon <= 84:
        base = rng.uniform(0.38, 0.58)

    # Himalayan foothills: 28-32°N, 76-82°E → moderate-high
    elif 28 <= center_lat <= 32 and 76 <= center_lon <= 84:
        base = rng.uniform(0.45, 0.65)

    # Thar Desert / Rajasthan: 24-30°N, 68-75°E → very low
    elif 24 <= center_lat <= 30 and 68 <= center_lon <= 76:
        base = rng.uniform(0.04, 0.18)

    # Sundarbans / coastal Bengal: 21-23°N, 88-90°E → high (mangrove)
    elif 21 <= center_lat <= 23 and 88 <= center_lon <= 91:
        base = rng.uniform(0.55, 0.72)

    # Default: moderate vegetation
    else:
        base = rng.uniform(0.28, 0.52)

    ndvi_mean = round(base, 4)
    ndvi_min  = round(max(0.01, base - rng.uniform(0.08, 0.18)), 4)
    ndvi_max  = round(min(0.98, base + rng.uniform(0.05, 0.15)), 4)

    return {
        "ndvi_mean": ndvi_mean,
        "ndvi_min":  ndvi_min,
        "ndvi_max":  ndvi_max,
        "data_source": "MOCK_MODIS_MOD13Q1",
        "pixel_count": rng.randint(120, 800),
    }


def _fetch_real_ndvi(bbox: dict) -> dict:
    """
    Fetch NDVI from NASA APPEEARS API.
    Requires NASA_APPEEARS_TOKEN in environment.

    Queries MOD13Q1.061 — MODIS Terra 250m NDVI, 16-day composite.
    """
    import requests

    token = os.getenv("NASA_APPEEARS_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}

    # APPEEARS point-sample endpoint (simpler than full task submission)
    # For production, use the full async task API for polygon statistics
    url = "https://appeears.earthdatacloud.nasa.gov/api/point/request"

    center_lat = (bbox["min_lat"] + bbox["max_lat"]) / 2
    center_lon = (bbox["min_lon"] + bbox["max_lon"]) / 2

    payload = {
        "task_type": "point",
        "task_name": "poc_ndvi_check",
        "params": {
            "coordinates": [{"longitude": center_lon, "latitude": center_lat, "id": "p1"}],
            "layers": [{"product": "MOD13Q1.061", "layer": "250m_16_days_NDVI"}],
            "dates": [{"startDate": "01-01-2023", "endDate": "12-31-2023"}],
            "output": {"format": {"type": "json"}}
        }
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()

    # Parse NDVI values from response
    data = resp.json()
    ndvi_values = [
        r["value"] / 10000  # MODIS stores NDVI as integer * 10000
        for r in data.get("results", [])
        if r.get("value", -3000) > -2000  # filter fill/cloud values
    ]

    if not ndvi_values:
        raise ValueError("No valid NDVI pixels returned from APPEEARS")

    return {
        "ndvi_mean": round(sum(ndvi_values) / len(ndvi_values), 4),
        "ndvi_min":  round(min(ndvi_values), 4),
        "ndvi_max":  round(max(ndvi_values), 4),
        "data_source": "NASA_APPEEARS_MOD13Q1.061",
        "pixel_count": len(ndvi_values),
    }


class SatelliteEvidenceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="SatelliteEvidenceAgent",
            system_prompt=SYSTEM_PROMPT,
        )

    def run(
        self,
        bbox: dict,
        company_text_claim: str = "",
        project_analysis_result: dict = None,
    ) -> dict:
        """
        Args:
            bbox: {"min_lon", "min_lat", "max_lon", "max_lat"}
            company_text_claim: original text from company
            project_analysis_result: output from ProjectAnalysisAgent

        Returns:
            dict with ndvi stats, forest_condition, satellite_trust_modifier, satellite_flags
        """
        logger.info(f"[SatelliteEvidenceAgent] Fetching NDVI for bbox: {bbox}")

        # Get NDVI — real API or mock
        if os.getenv("NASA_APPEEARS_TOKEN"):
            logger.info("[SatelliteEvidenceAgent] Using NASA APPEEARS API")
            ndvi_data = _fetch_real_ndvi(bbox)
        else:
            logger.info("[SatelliteEvidenceAgent] NASA_APPEEARS_TOKEN not set — using mock NDVI")
            ndvi_data = _mock_ndvi(bbox)

        logger.info(f"[SatelliteEvidenceAgent] NDVI mean={ndvi_data['ndvi_mean']}, source={ndvi_data['data_source']}")

        # LLM interprets the NDVI in context of the claim
        prompt = self._build_prompt(
            ndvi_data=ndvi_data,
            bounding_box=bbox,
            company_text_claim=company_text_claim or "Not provided",
            spatial_analysis_summary={
                "claimed_hectares": (project_analysis_result or {}).get("claimed_hectares"),
                "overlap_percent": (project_analysis_result or {}).get("overlap_percent"),
                "state": (project_analysis_result or {}).get("state"),
                "risk_level": (project_analysis_result or {}).get("risk_level"),
            },
        )

        raw = self._call_llm(prompt)
        result = self._parse_json(raw)

        # Always preserve the raw NDVI numbers from the data source
        result["ndvi_mean"]  = ndvi_data["ndvi_mean"]
        result["ndvi_min"]   = ndvi_data["ndvi_min"]
        result["ndvi_max"]   = ndvi_data["ndvi_max"]
        result["ndvi_source"] = ndvi_data["data_source"]
        result["ndvi_pixel_count"] = ndvi_data.get("pixel_count")

        logger.info(
            f"[SatelliteEvidenceAgent] condition={result.get('forest_condition')}, "
            f"modifier={result.get('satellite_trust_modifier')}"
        )
        return result