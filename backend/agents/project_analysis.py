"""
project_analysis.py — Parses company KMZ + text claims, runs spatial comparison.
"""

import json
import logging
import os

import geopandas as gpd

from agents.base_agent import BaseAgent
from tools.kmz_parser import parse_kmz, get_area_hectares, get_bounding_box
from tools.geospatial import (
    compare_claim_to_reference,
    check_protected_area_overlap,
    load_reference,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a senior carbon credit verification analyst specializing in Indian forestry projects.

You will receive:
1. Geospatial analysis results comparing the company's claimed area to verified reference data
2. The company's own text description of their project

Your job is to assess the credibility of the carbon credit claim and identify red flags.

Return ONLY a valid JSON object with these exact fields:
{
  "project_name": "<extracted from text or 'Unknown'>",
  "company_name": "<extracted from text or 'Unknown'>",
  "project_type": "<ARR|REDD+|UNKNOWN>",
  "state": "<Indian state where project is located>",
  "forest_type": "<type of forest claimed>",
  "claimed_area_ha": <number>,
  "verified_area_ha": <number>,
  "overlap_percent": <number>,
  "risk_level": "<one of: LOW, MEDIUM, HIGH, CRITICAL>",
  "trust_score": <number 0-100>,
  "analysis_flags": ["<flag1>", "<flag2>"],
  "red_flags": ["<serious concern1>", ...],
  "summary": "<2-3 sentence plain English assessment>"
}

Project Type Classification Rules:
- ARR: (Afforestation, Reforestation, and Revegetation). Use this if the project describes planting new trees, restoring degraded land, working on non-forest land, or mentions keywords like "AR", "ARR", "A/R", "Reforestation", "Afforestation", "Planting", "CDM", "CER".
- REDD+: (Reducing Emissions from Deforestation and Forest Degradation). Use this if the project focuses on protecting existing forests, preventing logging/clearing, or mentions keywords like "REDD", "Avoided Deforestation", "Conservation", "Protection".
- UNKNOWN: Use if neither is clear.

Risk level guide:
- LOW: 
    - REDD+: overlap > 80%, no protected area issues, consistent claims.
    - ARR: overlap 0-100% (not a risk factor), no protected area issues, consistent claims.
- MEDIUM: 
    - REDD+: overlap 50-80%, minor inconsistencies.
    - ARR: minor inconsistencies in text vs KMZ or state.
- HIGH: 
    - REDD+: overlap 20-50%, suspicious claims.
    - ARR: suspicious text claims, major inconsistencies (not relating to forest overlap).
- CRITICAL: 
    - ALL: protected area fraud, fabricated figures, or KMZ/claim total contradiction.
    - REDD+: overlap < 20%.

Trust score = weighted combination of spatial overlap (60% for REDD+, but 0% for ARR - use claim consistency 70% and area accuracy 30% for ARR), claim consistency, and area accuracy.
"""


class ProjectAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="ProjectAnalysisAgent",
            system_prompt=SYSTEM_PROMPT,
        )

    def _detect_project_type_deterministically(self, text: str) -> str:
        """
        Keyword-based fallback for project type detection.
        """
        text = text.lower()
        if any(k in text for k in ["reforestation", "afforestation", "arr", "a/r", "planting", "cdm", "cer", "planting"]):
            return "ARR"
        if any(k in text for k in ["redd", "avoided deforestation", "conservation", "protection", "preservation"]):
            return "REDD+"
        return "UNKNOWN"

    def run(self, kmz_path: str, company_text_claim: str = "") -> dict:
        """
        Full analysis pipeline:
        1. Parse KMZ
        2. Load reference data (PostGIS or local file)
        3. Spatial comparison
        4. Protected area check
        5. LLM reasoning
        6. Return structured verdict
        """
        logger.info(f"[ProjectAnalysisAgent] Starting analysis for: {kmz_path}")

        # ── Step 0: Deterministic check ──
        det_type = self._detect_project_type_deterministically(company_text_claim)

        # ── Step 1: Parse company's KMZ ──
        try:
            company_gdf = parse_kmz(kmz_path)
        except Exception as e:
            raise ValueError(f"Failed to parse KMZ: {e}")

        bbox = get_bounding_box(company_gdf)
        claimed_ha = get_area_hectares(company_gdf)
        logger.info(f"Company claim: {claimed_ha} ha, bbox: {bbox}")

        # ── Step 2: Load reference data ──
        forest_ref = load_reference(bbox, layer="forest_cover")
        pa_ref = load_reference(bbox, layer="protected_areas")

        # ── Step 3: Spatial comparison ──
        geo_result = compare_claim_to_reference(company_gdf, forest_ref)

        # ── Step 4: Protected area check ──
        pa_result = check_protected_area_overlap(company_gdf, pa_ref)

        # Merge all flags
        all_flags = geo_result["flags"] + pa_result["flags"]

        # ── Step 5: LLM reasoning ──
        combined_geo = {
            **geo_result,
            "protected_area_overlap_ha": pa_result["protected_area_overlap_ha"],
            "protected_area_overlap_pct": pa_result["protected_area_overlap_pct"],
            "bounding_box": bbox,
            "all_flags": all_flags,
            "deterministic_type": det_type,
        }

        prompt = self._build_prompt(
            company_text_claim=company_text_claim or "No text claim provided",
            geospatial_analysis=combined_geo,
        )

        raw = self._call_llm(prompt)
        result = self._parse_json(raw)

        # ── Step 6: Ensure raw geo numbers are preserved (don't let LLM hallucinate them) ──
        result["claimed_hectares"] = geo_result["claimed_hectares"]
        result["verified_hectares"] = geo_result["verified_hectares"]
        result["overlap_percent"] = geo_result["overlap_percent"]
        result["protected_area_overlap_ha"] = pa_result["protected_area_overlap_ha"]
        result["bbox"] = bbox
        result["all_flags"] = all_flags
        
        # Prefer LLM detection if it's not UNKNOWN, else fallback to deterministic
        if result.get("project_type", "UNKNOWN") == "UNKNOWN" and det_type != "UNKNOWN":
            result["project_type"] = det_type
        
        # ── Step 7: Area mismatch check (text claim vs KMZ measurement) ─────
        # The LLM extracts "claimed_area_ha" from the company's text description.
        # Compare this against the actual KMZ-measured area to catch overclaiming
        # or description fraud where the text says a different size than the file.
        try:
            text_ha = result.get("claimed_area_ha")
            kmz_ha  = geo_result["claimed_hectares"]
            if text_ha and float(text_ha) > 0 and kmz_ha > 0:
                text_ha = float(text_ha)
                diff_pct = abs(text_ha - kmz_ha) / kmz_ha * 100
                result["text_claimed_ha"] = text_ha
                result["area_mismatch_pct"] = round(diff_pct, 1)

                if diff_pct > 200:
                    result["all_flags"].append(
                        f"CRITICAL: Area mismatch — company text claims {text_ha:.0f} ha "
                        f"but KMZ file measures {kmz_ha:.1f} ha ({diff_pct:.0f}% difference). "
                        f"Possible description fraud or fabricated figures."
                    )
                elif diff_pct > 50:
                    result["all_flags"].append(
                        f"WARNING: Area mismatch — company text claims {text_ha:.0f} ha "
                        f"but KMZ file measures {kmz_ha:.1f} ha ({diff_pct:.0f}% difference)."
                    )
                elif diff_pct > 20:
                    result["all_flags"].append(
                        f"Minor area discrepancy: text claims {text_ha:.0f} ha, "
                        f"KMZ measures {kmz_ha:.1f} ha ({diff_pct:.0f}% difference)."
                    )
        except (TypeError, ValueError):
            pass  # if LLM didn't extract a numeric area, skip silently

        logger.info(
            f"[ProjectAnalysisAgent] Result: type={result.get('project_type')}, "
            f"risk={result.get('risk_level')}, "
            f"trust={result.get('trust_score')}, overlap={result.get('overlap_percent')}%, "
            f"area_mismatch={result.get('area_mismatch_pct', 'N/A')}%"
        )
        return result
