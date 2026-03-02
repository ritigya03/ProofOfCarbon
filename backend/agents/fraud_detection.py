"""
agents/fraud_detection.py — Identifies suspicious patterns across all agent outputs.

Receives the combined results from ProjectAnalysisAgent + SatelliteEvidenceAgent
and looks for fraud signals: overclaiming, inconsistencies, double-counting risk,
suspiciously round numbers, and cross-signal contradictions.
"""

import logging
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a forensic carbon credit fraud analyst specialising in Indian forestry projects.

You will receive the combined output from prior analysis stages:
1. Spatial analysis — forest cover overlap
2. Satellite NDVI analysis — vegetation signals
3. Baseline analysis — additionality values
4. PROJECT_TYPE — ARR or REDD+

Your job is to identify fraud signals ACROSS all data sources, adjusted by project context.

FRAUD PATTERNS BY PROJECT TYPE:

- PHANTOM FOREST:
    - REDD+: Claimed area has very low NDVI (<0.3) but company claims dense forest. (HIGH SUSPICION)
    - ARR: Low NDVI at start is NORMAL. If NDVI is very HIGH (>0.7) at start, it might be "Baseline Inflation" (claiming existing forest as new). (SUSPECTED)

- AREA INFLATION:
    - REDD+: Claimed hectares far exceed verified forest hectares (>2x). (HIGH SUSPICION)
    - ARR: Compare claimed KMZ area (`claimed_hectares`) vs company text claim (`text_claimed_ha`). 
    - **CRITICAL ARR RULE**: Do NOT compare against `verified_hectares` (forest cover) for ARR, as 0% forest is normal at start. High mismatch between KMZ and text claim is the only inflation signal for ARR.

- SIGNAL CONTRADICTION:
    - REDD+: Spatial data says 90% forest but NDVI says 0.2 (ARID). (CONFIRMED FRAUD)
    - ARR: NDVI trending DOWN but company claims successful growth. (CONFIRMED FRAUD)

- PROTECTED AREA LAUNDERING: Claiming credits for land already under legal protection (Forest Dept land, Sanctuaries). (CRITICAL)

Return ONLY a valid JSON object:
{
  "fraud_patterns": {
    "phantom_forest": "<CONFIRMED|SUSPECTED|POSSIBLE|CLEAR>",
    "area_inflation": "<CONFIRMED|SUSPECTED|POSSIBLE|CLEAR>",
    "signal_contradiction": "<CONFIRMED|SUSPECTED|POSSIBLE|CLEAR>",
    "protected_area_laundering": "<CONFIRMED|SUSPECTED|POSSIBLE|CLEAR>",
    "baseline_manipulation": "<CONFIRMED|SUSPECTED|POSSIBLE|CLEAR>"
  },
  "anomaly_score": <integer 0-100, where 100 = highly anomalous>,
  "fraud_flags": ["<specific flag 1>", "<specific flag 2>"],
  "fraud_risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "fraud_summary": "<2-3 sentences explaining findings based on project type context>"
}

Anomaly Score Guidance:
- 0-20: Clean, consistent signals.
- 41-60: Suspicious signals (e.g., ARR with high starting NDVI, or REDD+ with low overlap).
- 81-100: Near-certain fraud.
"""


class FraudDetectionAgent(BaseAgent):
    """
    Cross-checks all prior agent outputs for fraud patterns.
    Does not call any external tools — purely LLM reasoning over structured data.
    """

    def __init__(self):
        super().__init__(
            name="FraudDetectionAgent",
            system_prompt=SYSTEM_PROMPT,
        )

    def run(self, combined_data: dict) -> dict:
        """
        Args:
            combined_data: merged dict of ProjectAnalysisAgent + SatelliteEvidenceAgent outputs

        Returns:
            dict with fraud pattern assessments, anomaly score, flags
        """
        logger.info(
            "[FraudDetectionAgent] Analysing combined signals for fraud patterns..."
        )

        # Pull the fields most relevant to fraud detection
        fraud_context = {
            "project_type": combined_data.get("project_type"),
            # Spatial signals
            "claimed_hectares": combined_data.get("claimed_hectares"),
            "verified_hectares": combined_data.get("verified_hectares"),
            "overlap_percent": combined_data.get("overlap_percent"),
            "protected_area_overlap_ha": combined_data.get("protected_area_overlap_ha"),
            "spatial_risk_level": combined_data.get("risk_level"),
            "spatial_flags": combined_data.get("all_flags", []),
            # Satellite signals
            "ndvi_current_mean": combined_data.get("ndvi_current_mean"),
            "ndvi_historical_mean": combined_data.get("ndvi_historical_mean"),
            "ndvi_trend": combined_data.get("ndvi_trend"),
            "ndvi_anomaly_score": combined_data.get("ndvi_anomaly_score"),
            "vegetation_class": combined_data.get("vegetation_class"),
            "satellite_risk_level": combined_data.get("satellite_risk_level"),
            "satellite_flags": combined_data.get("satellite_flags", []),
            # Baseline signals
            "additionality_score": combined_data.get("additionality_score"),
            "deforestation_pressure": combined_data.get("deforestation_pressure"),
            "baseline_summary": combined_data.get("baseline_summary"),
            # Company claim
            "company_name": combined_data.get("company_name"),
            "project_name": combined_data.get("project_name"),
            "state": combined_data.get("state"),
            "forest_type": combined_data.get("forest_type"),
            # Area mismatch (text description vs KMZ file)
            "text_claimed_ha": combined_data.get("text_claimed_ha"),
            "area_mismatch_pct": combined_data.get("area_mismatch_pct"),
        }

        prompt = self._build_prompt(
            combined_analysis_data=fraud_context,
            instruction=(
                "Identify all fraud patterns present. Be specific — reference actual numbers "
                "from the data to justify each finding. Do not invent signals not present in the data."
            ),
        )

        raw = self._call_llm(prompt)
        result = self._parse_json(raw)

        logger.info(
            f"[FraudDetectionAgent] anomaly_score={result.get('anomaly_score')}, "
            f"fraud_risk={result.get('fraud_risk_level')}, "
            f"flags={len(result.get('fraud_flags', []))}"
        )

        return result
