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

You will receive analysis from four specialist agents:
1. Spatial Analysis    — forest cover overlap (REDD+) or area accuracy (ARR)
2. Satellite Evidence  — NDVI levels and vegetation growth trends
3. Baseline Analysis   — additionality (Avoided loss for REDD+, Sequestration for ARR)
4. Fraud Detection     — cross-signal fraud patterns

IMPORTANT — DATA QUALITY LIMITATIONS:
- OpenStreetMap (OSM) forest data is INCOMPLETE for many Indian states. Low overlap may reflect missing OSM polygons, NOT actual lack of forest.
- NDVI satellite data has seasonal and resolution limitations. A 5-15% decline may be seasonal, not deforestation.
- If overlap is 30-60%, do NOT assume fraud — the reference data may be incomplete. Use the NDVI and other evidence to cross-validate.
- Only flag low overlap as fraud if NDVI ALSO shows bare/sparse vegetation (< 0.30).

PROJECT EVALUATION PATHWAYS:

- REDD+ (Avoided Deforestation):
    - Priority: Forest overlap AND NDVI evidence together. Neither alone is conclusive.
    - Overlap > 70%: Strong spatial evidence.
    - Overlap 30-70%: Inconclusive — rely on NDVI and satellite evidence to decide.
    - Overlap < 30% AND NDVI < 0.3: Likely fraudulent.
    - Overlap < 30% BUT NDVI > 0.5: Data gap — OSM likely incomplete. Give benefit of doubt.
    - Weights: Spatial (30%), Satellite NDVI (30%), Baseline (20%), Fraud detection (20%).

- ARR (Afforestation/Reforestation):
    - Priority: High additionality (sequestration delta) and positive NDVI trend (increasing).
    - Low overlap with existing forest is EXPECTED and NORMAL for ARR.
    - Weights: Additionality (35%), Satellite Trend (30%), Baseline (20%), Fraud detection (15%).

- UNKNOWN project type:
    - If project type is unknown, evaluate generously using both pathways.
    - Do NOT penalise harshly for unknown type — the company description may simply lack the specific keyword.

Verdict categories:
- VERIFIED:         Trust >= 70. Strong evidence, no serious fraud signals.
- CONDITIONALLY_VERIFIED: Trust 45-69. Mostly credible, minor issues or data gaps.
- REQUIRES_REVIEW:  Trust 25-44. Significant concerns, but not conclusive fraud.
- REJECTED:         Trust < 25. Clear fraud evidence (e.g., NDVI < 0.2 with forest claims, protected area overlap > 50%, confirmed phantom forest).

CRITICAL RULES:
- Do NOT reject a project SOLELY based on low overlap. You MUST have at least TWO independent fraud signals (overlap + NDVI, or overlap + protected area, etc.).
- If overlap is moderate (30-60%) but NDVI shows moderate-to-good vegetation (> 0.4), the verdict should be CONDITIONALLY_VERIFIED or REQUIRES_REVIEW, NOT REJECTED.
- Always mention data quality limitations in the verification_summary when relevant.

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
  "verification_summary": "<3-4 sentence summary suitable for a public audit report, explicitly mentioning PROJECT_TYPE and any data quality caveats>"
}

Be balanced. Acknowledge uncertainty. If data is ambiguous, err on the side of REQUIRES_REVIEW rather than REJECTED.
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
            "project_type": combined_data.get("project_type"),
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
            # Baseline
            "additionality_score": combined_data.get("additionality_score"),
            "additionality_verdict": combined_data.get("additionality_verdict"),
            "baseline_summary": combined_data.get("baseline_summary"),
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
