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

Risk level guide:
- LOW: overlap > 80%, no protected area issues, consistent claims
- MEDIUM: overlap 50-80%, minor inconsistencies
- HIGH: overlap 20-50%, suspicious claims
- CRITICAL: overlap < 20%, or protected area fraud, or major overclaim

Trust score = weighted combination of spatial overlap (60%), claim consistency (25%), area accuracy (15%).
"""


class ProjectAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="ProjectAnalysisAgent",
            system_prompt=SYSTEM_PROMPT,
        )

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

        logger.info(
            f"[ProjectAnalysisAgent] Result: risk={result.get('risk_level')}, "
            f"trust={result.get('trust_score')}, overlap={result.get('overlap_percent')}%"
        )
        return result
