"""
historical_baseline.py — Assesses whether a carbon credit claim has genuine additionality.

"Additionality" is the most important and most abused concept in carbon markets.
It answers: would the forest have survived anyway, even without this carbon project?

If YES → the credits are not additional → they represent no real climate benefit.
If NO  → forest was genuinely under threat → the project creates real value.

This agent combines:
  1. Deterministic baseline metrics (state deforestation rates, forest type data)
  2. LLM reasoning to contextualise metrics against the company's specific claim
"""

import logging
from agents.base_agent import BaseAgent
from tools.baseline import compute_additionality_metrics

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a carbon market additionality expert specialising in Indian REDD+ and afforestation projects.

You will receive:
1. Computed baseline metrics: historical deforestation rate (REDD+) or natural regeneration baseline (ARR).
2. The company's text description of their project.
3. Key results from prior spatial and satellite analysis, including PROJECT_TYPE.

Your job is to assess whether the carbon credits have genuine ADDITIONALITY.

ADDITIONALITY BY PROJECT TYPE:
- REDD+: Would the forest have been lost anyway WITHOUT this project? High additionality if deforestation pressure is high.
- ARR: Would the forest have failed to grow back naturally WITHOUT this project? High additionality if natural regeneration is slow/unlikely and project significantly increases carbon sequestration.

Key concepts:
- ADDITIONALITY SCORE (0-100): High score means strong additionality case.
- DEFORESTATION PRESSURE (REDD+): Critical for REDD+ additionality.
- SEQUESTRATION DELTA (ARR): The difference between project growth and counterfactual growth.

Return ONLY a valid JSON object with these exact fields:
{
  "additionality_verdict": "<one of: STRONG, MODERATE, WEAK, NEGLIGIBLE>",
  "baseline_risk_level": "<one of: LOW, MEDIUM, HIGH, CRITICAL>",
  "baseline_trust_modifier": <integer, -25 to +15>,
  "counterfactual_assessment": "<1-2 sentences: what would have happened to this land/forest without the project>",
  "permanence_assessment": "<1-2 sentences: how likely is the sequestered carbon to stay stored>",
  "additionality_flags": ["<flag1>", "<flag2>"],
  "baseline_summary": "<2-3 sentence assessment of the additionality claim in context of the project type>"
}

Scoring baseline_trust_modifier:
- STRONG additionality: +10 to +15
- MODERATE additionality: +3 to +8
- WEAK additionality: -8 to -3
- NEGLIGIBLE additionality: -20 to -10
- High permanence risk: subtract additional 5
"""


class HistoricalBaselineAgent(BaseAgent):
    """
    Assesses additionality by computing a historical baseline scenario
    and using an LLM to reason about whether the project creates genuine
    climate benefit beyond business-as-usual.
    """

    def __init__(self):
        super().__init__(
            name="HistoricalBaselineAgent",
            system_prompt=SYSTEM_PROMPT,
        )

    def run(
        self,
        state: str,
        forest_type: str,
        claimed_ha: float,
        company_text_claim: str = "",
        project_start_year: int = 2020,
        credit_period_years: int = 10,
        prior_results: dict | None = None,
    ) -> dict:
        """
        Run historical baseline + additionality analysis.

        Args:
            state:               Indian state where project is located
            forest_type:         Type of forest (dense, mangrove, open, etc.)
            claimed_ha:          Total project area in hectares
            company_text_claim:  Raw text from the company's submission
            project_start_year:  Year the project intervention began
            credit_period_years: Duration over which credits are being claimed
            prior_results:       Combined dict from ProjectAnalysisAgent + SatelliteEvidenceAgent

        Returns:
            dict with baseline metrics + LLM additionality verdict
        """
        logger.info(
            f"[HistoricalBaselineAgent] Computing baseline — "
            f"state={state}, forest_type={forest_type}, "
            f"area={claimed_ha}ha, period={project_start_year}+{credit_period_years}yr"
        )

        # ── Step 1: Compute deterministic baseline metrics ────────────────────
        project_type = "REDD+"
        if prior_results and prior_results.get("project_type"):
            project_type = prior_results.get("project_type")

        baseline_metrics = compute_additionality_metrics(
            state=state,
            forest_type=forest_type,
            claimed_ha=claimed_ha,
            project_start_year=project_start_year,
            credit_period_years=credit_period_years,
            project_type=project_type,
        )

        logger.info(
            f"[HistoricalBaselineAgent] Baseline computed — "
            f"pressure={baseline_metrics['deforestation_pressure']}, "
            f"additionality_score={baseline_metrics['additionality_score']}, "
            f"counterfactual_loss={baseline_metrics['counterfactual_loss_ha']}ha"
        )

        # ── Step 2: Build context from prior agents ───────────────────────────
        prior_context = {}
        if prior_results:
            prior_context = {
                "spatial_overlap_pct":       prior_results.get("overlap_percent"),
                "spatial_risk_level":        prior_results.get("risk_level"),
                "satellite_vegetation_class":prior_results.get("vegetation_class"),
                "ndvi_current":              prior_results.get("ndvi_current_mean"),
                "ndvi_trend":                prior_results.get("ndvi_trend"),
                "satellite_risk_level":      prior_results.get("satellite_risk_level"),
                "protected_area_overlap_ha": prior_results.get("protected_area_overlap_ha"),
                "prior_flags": (
                    prior_results.get("all_flags", []) +
                    prior_results.get("satellite_flags", [])
                ),
            }

        # ── Step 3: LLM reasoning ─────────────────────────────────────────────
        prompt = self._build_prompt(
            company_text_claim=company_text_claim or "No text claim provided",
            baseline_metrics=baseline_metrics,
            prior_analysis_context=prior_context,
        )

        raw    = self._call_llm(prompt)
        result = self._parse_json(raw)

        # ── Step 4: Lock in deterministic numbers (no LLM hallucination) ─────
        result["state"]                       = baseline_metrics["state"]
        result["annual_deforestation_pct"]    = baseline_metrics["annual_deforestation_pct"]
        result["deforestation_pressure"]      = baseline_metrics["deforestation_pressure"]
        result["primary_drivers"]             = baseline_metrics["primary_drivers"]
        result["forest_type_resolved"]        = baseline_metrics["forest_type_resolved"]
        result["permanence_risk"]             = baseline_metrics["permanence_risk"]
        result["avg_carbon_stock_t_ha"]       = baseline_metrics["avg_carbon_stock_t_ha"]
        result["counterfactual_loss_ha"]      = baseline_metrics["counterfactual_loss_ha"]
        result["counterfactual_loss_pct"]     = baseline_metrics["counterfactual_loss_pct"]
        result["carbon_at_risk_tonnes_co2e"]  = baseline_metrics["carbon_at_risk_tonnes_co2e"]
        result["additionality_score"]         = baseline_metrics["additionality_score"]
        result["required_buffer_pct"]         = baseline_metrics["required_buffer_pct"]
        result["credit_period_years"]         = credit_period_years
        result["project_start_year"]          = project_start_year

        # Merge tool flags with LLM flags (deduplicated)
        tool_flags = baseline_metrics["baseline_flags"]
        llm_flags  = result.get("additionality_flags", [])
        result["additionality_flags"] = tool_flags + [f for f in llm_flags if f not in tool_flags]

        logger.info(
            f"[HistoricalBaselineAgent] Done — "
            f"verdict={result.get('additionality_verdict')}, "
            f"modifier={result.get('baseline_trust_modifier')}"
        )
        return result