"""
agents/fraud_detection.py — Identifies suspicious patterns across all agent outputs.

Receives the combined results from ProjectAnalysisAgent + SatelliteEvidenceAgent
and looks for fraud signals: overclaiming, inconsistencies, double-counting risk,
suspiciously round numbers, and cross-signal contradictions.

Now includes an ML model (XGBoost) for deterministic scoring alongside LLM reasoning.
"""

import logging
import os
from pathlib import Path

import numpy as np

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# ── ML feature columns (must match training data) ────────────────────────────
ML_FEATURE_COLS = [
    "overlap_percent",
    "claimed_hectares",
    "verified_hectares",
    "area_ratio",
    "protected_area_overlap_ha",
    "ndvi_current_mean",
    "ndvi_historical_mean",
    "ndvi_change",
    "ndvi_anomaly_score",
    "additionality_score",
    "is_arr",
    "area_mismatch_pct",
    "flag_count",
]

# ML label mapping
ML_LABEL_MAP = {
    0: "VERIFIED",
    1: "CONDITIONALLY_VERIFIED",
    2: "REQUIRES_REVIEW",
    3: "REJECTED",
}

# Map ML verdict → fraud risk level
ML_VERDICT_TO_RISK = {
    "VERIFIED": "LOW",
    "CONDITIONALLY_VERIFIED": "MEDIUM",
    "REQUIRES_REVIEW": "HIGH",
    "REJECTED": "CRITICAL",
}

SYSTEM_PROMPT = """
You are a forensic carbon credit fraud analyst specialising in Indian forestry projects.

You will receive the combined output from prior analysis stages:
1. Spatial analysis — forest cover overlap
2. Satellite NDVI analysis — vegetation signals
3. Baseline analysis — additionality values
4. PROJECT_TYPE — ARR or REDD+
5. ML MODEL PREDICTION — a machine learning model's score and risk assessment

Your job is to identify fraud signals ACROSS all data sources, adjusted by project context.
Use the ML model's prediction as a reference point, but apply your own reasoning.

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
  "fraud_flags": ["<specific flag 1>", "<specific flag 2>"],
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

    Uses a two-pronged approach:
      1. ML model (XGBoost) — deterministic anomaly score and risk level
      2. LLM (Groq/Llama)  — human-readable reasoning, fraud patterns, and flags

    If the ML model is not available (model file missing), falls back to LLM-only mode.
    """

    def __init__(self):
        super().__init__(
            name="FraudDetectionAgent",
            system_prompt=SYSTEM_PROMPT,
        )
        self.ml_model = self._load_ml_model()

    def _load_ml_model(self):
        """Load the trained XGBoost model. Returns None if not available."""
        model_path = Path(__file__).parent.parent / "ml" / "models" / "fraud_model.json"
        if not model_path.exists():
            logger.warning(
                f"[FraudDetectionAgent] ML model not found at {model_path}. "
                f"Running in LLM-only mode. Train the model with: python -m ml.train_model"
            )
            return None

        try:
            from xgboost import XGBClassifier
            model = XGBClassifier()
            model.load_model(str(model_path))
            logger.info(f"[FraudDetectionAgent] ML model loaded from {model_path}")
            return model
        except Exception as e:
            logger.warning(f"[FraudDetectionAgent] Failed to load ML model: {e}")
            return None

    def _extract_features(self, combined_data: dict) -> np.ndarray:
        """
        Extract the 13-feature vector from pipeline data for ML prediction.

        This mirrors the features used during training (ml/generate_training_data.py).
        Missing values are replaced with safe defaults.
        """
        claimed = float(combined_data.get("claimed_hectares", 0) or 0)
        verified = float(combined_data.get("verified_hectares", 0) or 0)
        ndvi_curr = float(combined_data.get("ndvi_current_mean", 0) or 0)
        ndvi_hist = float(combined_data.get("ndvi_historical_mean", 0) or 0)
        project_type = str(combined_data.get("project_type", "REDD+")).upper()

        # Count only SERIOUS flags (not informational warnings or INFO notes)
        # This prevents legitimate projects with many soft warnings from being
        # classified as fraudulent due to inflated flag_count.
        _serious_keywords = ["CRITICAL", "overclaim", "fraud", "fabricat", "contradiction", "mismatch"]
        all_flags = combined_data.get("all_flags", []) + combined_data.get("satellite_flags", [])
        flag_count = sum(
            1 for f in all_flags
            if any(kw.lower() in f.lower() for kw in _serious_keywords)
        )

        features = {
            "overlap_percent": float(combined_data.get("overlap_percent", 0) or 0),
            "claimed_hectares": claimed,
            "verified_hectares": verified,
            "area_ratio": verified / claimed if claimed > 0 else 0,
            "protected_area_overlap_ha": float(
                combined_data.get("protected_area_overlap_ha", 0) or 0
            ),
            "ndvi_current_mean": ndvi_curr,
            "ndvi_historical_mean": ndvi_hist,
            "ndvi_change": ndvi_curr - ndvi_hist,
            "ndvi_anomaly_score": float(
                combined_data.get("ndvi_anomaly_score", 0) or 0
            ),
            "additionality_score": float(
                combined_data.get("additionality_score", 50) or 50
            ),
            "is_arr": 1 if "ARR" in project_type else 0,
            "area_mismatch_pct": float(
                combined_data.get("area_mismatch_pct", 0) or 0
            ),
            "flag_count": flag_count,
        }

        # Build array in the exact column order used during training
        return np.array([[features[col] for col in ML_FEATURE_COLS]], dtype=np.float32)

    def _ml_predict(self, combined_data: dict) -> dict:
        """
        Run ML model inference.

        Returns:
            dict with ml_anomaly_score (0-100), ml_fraud_risk_level, ml_verdict,
            and ml_class_probabilities
        """
        if self.ml_model is None:
            return {}

        try:
            features = self._extract_features(combined_data)
            proba = self.ml_model.predict_proba(features)[0]
            predicted_class = int(np.argmax(proba))
            verdict = ML_LABEL_MAP[predicted_class]
            risk_level = ML_VERDICT_TO_RISK[verdict]

            # Anomaly score: weighted average of probabilities
            # Aggressive weights can penalise partial data too heavily.
            # Using slightly more conservative weights:
            # VERIFIED (0), CONDITIONALLY (10), REVIEW (40), REJECTED (90)
            weights = np.array([0, 10, 40, 90])  
            anomaly_score = int(np.round(np.dot(proba, weights)))

            ml_result = {
                "ml_anomaly_score": anomaly_score,
                "ml_fraud_risk_level": risk_level,
                "ml_verdict": verdict,
                "ml_confidence": round(float(proba[predicted_class]), 3),
                "ml_class_probabilities": {
                    ML_LABEL_MAP[i]: round(float(p), 3)
                    for i, p in enumerate(proba)
                },
            }

            logger.info(
                f"[FraudDetectionAgent] ML prediction: {verdict} "
                f"(confidence={ml_result['ml_confidence']}, "
                f"anomaly_score={anomaly_score})"
            )
            return ml_result

        except Exception as e:
            logger.warning(f"[FraudDetectionAgent] ML prediction failed: {e}")
            return {}

    def run(self, combined_data: dict) -> dict:
        """
        Args:
            combined_data: merged dict of ProjectAnalysisAgent + SatelliteEvidenceAgent outputs

        Returns:
            dict with fraud pattern assessments, anomaly score, flags.
            If ML model is available, anomaly_score and fraud_risk_level come from ML.
            LLM always provides fraud_patterns, fraud_flags, and fraud_summary.
        """
        logger.info(
            "[FraudDetectionAgent] Analysing combined signals for fraud patterns..."
        )

        # ── Step 1: ML prediction (deterministic, fast) ──────────────────────
        ml_result = self._ml_predict(combined_data)

        # ── Step 2: Build context for LLM ────────────────────────────────────
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

        # Include ML prediction in context for LLM to reference
        if ml_result:
            fraud_context["ml_model_prediction"] = {
                "ml_anomaly_score": ml_result.get("ml_anomaly_score"),
                "ml_fraud_risk_level": ml_result.get("ml_fraud_risk_level"),
                "ml_verdict": ml_result.get("ml_verdict"),
                "ml_confidence": ml_result.get("ml_confidence"),
            }

        # ── Step 3: LLM reasoning ───────────────────────────────────────────
        prompt = self._build_prompt(
            combined_analysis_data=fraud_context,
            instruction=(
                "Identify all fraud patterns present. Be specific — reference actual numbers "
                "from the data to justify each finding. Do not invent signals not present in the data."
            ),
        )

        raw = self._call_llm(prompt)
        result = self._parse_json(raw)

        # ── Step 4: Merge ML + LLM outputs ──────────────────────────────────
        # ML model provides the hard numbers (deterministic, reproducible)
        # LLM provides the reasoning (fraud_patterns, fraud_flags, fraud_summary)
        if ml_result:
            result["anomaly_score"] = ml_result["ml_anomaly_score"]
            result["fraud_risk_level"] = ml_result["ml_fraud_risk_level"]
            # Preserve ML metadata in the output
            result["ml_anomaly_score"] = ml_result["ml_anomaly_score"]
            result["ml_fraud_risk_level"] = ml_result["ml_fraud_risk_level"]
            result["ml_verdict"] = ml_result["ml_verdict"]
            result["ml_confidence"] = ml_result["ml_confidence"]
            result["ml_class_probabilities"] = ml_result["ml_class_probabilities"]

        logger.info(
            f"[FraudDetectionAgent] anomaly_score={result.get('anomaly_score')}, "
            f"fraud_risk={result.get('fraud_risk_level')}, "
            f"flags={len(result.get('fraud_flags', []))}, "
            f"ml_available={'yes' if ml_result else 'no'}"
        )

        return result
