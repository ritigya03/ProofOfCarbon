"""
agents/verifier.py — Final aggregation agent. Produces the definitive verdict.

Receives all prior agent outputs and produces a single, authoritative
trust score, verdict, and human-readable explanation.
"""

import logging
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are the Chief Carbon Credit Verification Officer for India's national carbon registry.

You will receive the complete analysis from three specialist agents:
1. Spatial Analysis    — geospatial overlap with verified forest reference data
2. Satellite Evidence  — NDVI vegetation data from NASA MODIS satellite
3. Fraud Detection     — cross-signal fraud pattern analysis

Your job is to produce the FINAL authoritative verdict on this carbon credit claim.

Weighting for final trust score:
- Spatial overlap analysis:  40% weight
- Satellite NDVI evidence:   30% weight
- Fraud detection clean bill: 30% weight

Verdict categories:
- VERIFIED:         Trust >= 75. Strong evidence, no serious fraud signals. Recommend approval.
- CONDITIONALLY_VERIFIED: Trust 55-74. Mostly credible but has minor issues. Recommend approval with conditions.
- REQUIRES_REVIEW:  Trust 35-54. Significant concerns. Recommend independent field verification before approval.
- REJECTED:         Trust < 35. Serious fraud signals, major overclaiming, or protected area violations. Recommend rejection.

Return ONLY a valid JSON object:
{
  "final_verdict": "<VERIFIED|CONDITIONALLY_VERIFIED|REQUIRES_REVIEW|REJECTED>",
  "final_trust_score": <integer 0-100>,
  "final_risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "confidence": "<HIGH|MEDIUM|LOW>",
  "key_findings": [
    "<most important finding 1>",
    "<most important finding 2>",
    "<most important finding 3>"
  ],
  "recommendation": "<one clear action sentence for the registry officer>",
  "verification_summary": "<3-4 sentence plain English summary suitable for a public audit report>"
}

Be decisive. A registry officer needs a clear recommendation, not hedging.
If data is contradictory, explain the contradiction in key_findings and default to REQUIRES_REVIEW.
"""


class VerifierAgent(BaseAgent):
    """
    Aggregates all agent outputs into a final verdict.
    The last agent in the pipeline — its output becomes the top-level response fields.
    """

    def __init__(self):
        super().__init__(
            name="VerifierAgent",
            system_prompt=SYSTEM_PROMPT,
        )

    def run(self, combined_data: dict) -> dict:
        """
        Args:
            combined_data: fully merged dict from all prior agents

        Returns:
            dict with final_verdict, final_trust_score, recommendation, etc.
        """
        logger.info("[VerifierAgent] Producing final verdict...")

        # Summarise all inputs for the LLM — don't dump the entire dict,
        # keep it focused on the decision-relevant fields
        summary_for_llm = {
            # Spatial
            "overlap_percent": combined_data.get("overlap_percent"),
            "claimed_hectares": combined_data.get("claimed_hectares"),
            "verified_hectares": combined_data.get("verified_hectares"),
            "protected_area_overlap_ha": combined_data.get("protected_area_overlap_ha"),
            "spatial_risk_level": combined_data.get("risk_level"),
            # Satellite
            "ndvi_current_mean": combined_data.get("ndvi_current_mean"),
            "ndvi_trend": combined_data.get("ndvi_trend"),
            "vegetation_class": combined_data.get("vegetation_class"),
            "satellite_risk_level": combined_data.get("satellite_risk_level"),
            "satellite_trust_modifier": combined_data.get("satellite_trust_modifier"),
            # Fraud
            "anomaly_score": combined_data.get("anomaly_score"),
            "fraud_risk_level": combined_data.get("fraud_risk_level"),
            "fraud_patterns": combined_data.get("fraud_patterns", {}),
            # Intermediate trust score going in
            "intermediate_trust_score": combined_data.get("trust_score"),
            # All accumulated flags
            "all_flags": (
                combined_data.get("all_flags", [])
                + combined_data.get("satellite_flags", [])
                + combined_data.get("fraud_flags", [])
            ),
            # Project identity
            "project_name": combined_data.get("project_name"),
            "company_name": combined_data.get("company_name"),
            "state": combined_data.get("state"),
        }

        prompt = self._build_prompt(
            complete_analysis=summary_for_llm,
            instruction=(
                "Produce the final verdict. Your final_trust_score should reflect the weighted "
                "combination of all three analysis stages. Be specific in key_findings — "
                "quote the actual numbers."
            ),
        )

        raw = self._call_llm(prompt)
        result = self._parse_json(raw)

        logger.info(
            f"[VerifierAgent] FINAL — verdict={result.get('final_verdict')}, "
            f"trust={result.get('final_trust_score')}, "
            f"confidence={result.get('confidence')}"
        )

        return result
