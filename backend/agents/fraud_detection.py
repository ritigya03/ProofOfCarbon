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

You will receive the combined output from two prior analysis stages:
1. Spatial analysis — how much of the claimed area is actually forest
2. Satellite NDVI analysis — what the satellite data shows about vegetation

Your job is to identify fraud signals, inconsistencies, and red flags ACROSS both data sources.

Known fraud patterns in Indian carbon markets:
- PHANTOM FOREST: Claimed area has very low NDVI (<0.2) but company claims dense forest
- PROTECTED AREA LAUNDERING: Claiming credits for land already under legal protection
- AREA INFLATION: Claimed hectares far exceed verified hectares (>2x)
- REGISTRY DOUBLE-COUNT: Same area registered with multiple carbon registries
- BASELINE MANIPULATION: Claiming forest that existed long before the project started
- SIGNAL CONTRADICTION: Spatial data says forest exists but NDVI says it doesn't (or vice versa)
- ROUND NUMBER ANOMALY: Suspiciously exact figures (exactly 1000 ha, exactly 50% overlap) suggest fabrication
- ADMINISTRATIVE MISMATCH: Claimed state/district doesn't match the actual coordinates

For each fraud pattern, assign a severity:
- CONFIRMED: Clear evidence in the data
- SUSPECTED: Strong indicators but not conclusive  
- POSSIBLE: Minor signals worth flagging
- CLEAR: No evidence of this pattern

Return ONLY a valid JSON object:
{
  "fraud_patterns": {
    "phantom_forest": "<CONFIRMED|SUSPECTED|POSSIBLE|CLEAR>",
    "area_inflation": "<CONFIRMED|SUSPECTED|POSSIBLE|CLEAR>",
    "signal_contradiction": "<CONFIRMED|SUSPECTED|POSSIBLE|CLEAR>",
    "protected_area_laundering": "<CONFIRMED|SUSPECTED|POSSIBLE|CLEAR>",
    "round_number_anomaly": "<CONFIRMED|SUSPECTED|POSSIBLE|CLEAR>",
    "administrative_mismatch": "<CONFIRMED|SUSPECTED|POSSIBLE|CLEAR>"
  },
  "anomaly_score": <integer 0-100, where 100 = highly anomalous>,
  "fraud_flags": ["<specific flag 1>", "<specific flag 2>"],
  "fraud_risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "fraud_summary": "<2-3 sentences explaining the key fraud signals found or absence thereof>"
}

anomaly_score guide:
- 0-20: Clean, consistent signals — credible claim
- 21-40: Minor inconsistencies — monitor but not disqualifying  
- 41-60: Multiple suspicious signals — enhanced scrutiny required
- 61-80: Strong fraud indicators — likely fraudulent
- 81-100: Near-certain fraud — recommend rejection
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
            # Company claim
            "company_name": combined_data.get("company_name"),
            "project_name": combined_data.get("project_name"),
            "state": combined_data.get("state"),
            "forest_type": combined_data.get("forest_type"),
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
