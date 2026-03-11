"""
ml/generate_training_data.py — Generates synthetic labeled training data
for the fraud detection ML model.

Each row simulates the merged output of all 4 upstream agents
(ProjectAnalysis, SatelliteEvidence, HistoricalBaseline, FraudDetection)
and is assigned a ground-truth label based on domain rules.

Usage:
    cd backend
    python -m ml.generate_training_data          # generates ~2000 rows
    python -m ml.generate_training_data --n 5000  # custom count
"""

import argparse
import os
import random
from pathlib import Path

import numpy as np
import pandas as pd


# ── Label definitions ────────────────────────────────────────────────────────
LABELS = {
    "VERIFIED": 0,
    "CONDITIONALLY_VERIFIED": 1,
    "REQUIRES_REVIEW": 2,
    "REJECTED": 3,
}


# ── Feature column names (13 features) ───────────────────────────────────────
FEATURE_COLS = [
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


def _clip(val, lo, hi):
    return max(lo, min(hi, val))


# ── Scenario generators ─────────────────────────────────────────────────────
# Each returns a dict of features + label.  Controlled randomness ensures
# diversity while keeping labels realistic.


def _gen_clean_redd(rng: np.random.Generator) -> dict:
    """Clean REDD+ claim — high overlap, good NDVI, low fraud signals → VERIFIED"""
    claimed = rng.uniform(200, 1500)
    overlap = rng.uniform(75, 98)
    verified = claimed * overlap / 100
    ndvi_hist = rng.uniform(0.55, 0.75)
    ndvi_curr = ndvi_hist + rng.uniform(-0.05, 0.08)
    return {
        "overlap_percent": round(overlap, 1),
        "claimed_hectares": round(claimed, 1),
        "verified_hectares": round(verified, 1),
        "area_ratio": round(verified / claimed, 3),
        "protected_area_overlap_ha": 0.0,
        "ndvi_current_mean": round(_clip(ndvi_curr, 0, 1), 3),
        "ndvi_historical_mean": round(ndvi_hist, 3),
        "ndvi_change": round(ndvi_curr - ndvi_hist, 3),
        "ndvi_anomaly_score": round(rng.uniform(0, 20), 1),
        "additionality_score": round(rng.uniform(55, 95), 1),
        "is_arr": 0,
        "area_mismatch_pct": round(rng.uniform(0, 10), 1),
        "flag_count": 0,  # clean projects have 0 serious flags
        "label": "VERIFIED",
    }


def _gen_clean_arr(rng: np.random.Generator) -> dict:
    """Clean ARR project — low starting NDVI (normal), high additionality → VERIFIED"""
    claimed = rng.uniform(100, 800)
    # For ARR, overlap with existing forest is low (expected — it's new planting)
    overlap = rng.uniform(0, 30)
    verified = claimed * overlap / 100
    ndvi_hist = rng.uniform(0.10, 0.35)
    ndvi_curr = ndvi_hist + rng.uniform(0.05, 0.25)  # growth trend
    return {
        "overlap_percent": round(overlap, 1),
        "claimed_hectares": round(claimed, 1),
        "verified_hectares": round(verified, 1),
        "area_ratio": round(verified / claimed if claimed > 0 else 0, 3),
        "protected_area_overlap_ha": 0.0,
        "ndvi_current_mean": round(_clip(ndvi_curr, 0, 1), 3),
        "ndvi_historical_mean": round(ndvi_hist, 3),
        "ndvi_change": round(ndvi_curr - ndvi_hist, 3),
        "ndvi_anomaly_score": round(rng.uniform(0, 25), 1),
        "additionality_score": round(rng.uniform(60, 95), 1),
        "is_arr": 1,
        "area_mismatch_pct": round(rng.uniform(0, 12), 1),
        "flag_count": 0,  # clean ARR projects have 0 serious flags
        "label": "VERIFIED",
    }


def _gen_area_inflation(rng: np.random.Generator) -> dict:
    """Area inflation — claims much more land than actually verified → REJECTED/REVIEW"""
    claimed = rng.uniform(1000, 5000)
    # Verified is much less — overclaiming
    verified = claimed * rng.uniform(0.02, 0.25)
    overlap = (verified / claimed) * 100
    ndvi_curr = rng.uniform(0.15, 0.50)
    ndvi_hist = ndvi_curr + rng.uniform(-0.10, 0.05)
    mismatch = rng.uniform(40, 200)

    # Severe cases get REJECTED, moderate get REQUIRES_REVIEW
    label = "REJECTED" if overlap < 15 else "REQUIRES_REVIEW"

    return {
        "overlap_percent": round(overlap, 1),
        "claimed_hectares": round(claimed, 1),
        "verified_hectares": round(verified, 1),
        "area_ratio": round(verified / claimed, 3),
        "protected_area_overlap_ha": round(rng.uniform(0, 50), 1),
        "ndvi_current_mean": round(_clip(ndvi_curr, 0, 1), 3),
        "ndvi_historical_mean": round(_clip(ndvi_hist, 0, 1), 3),
        "ndvi_change": round(ndvi_curr - ndvi_hist, 3),
        "ndvi_anomaly_score": round(rng.uniform(40, 85), 1),
        "additionality_score": round(rng.uniform(10, 50), 1),
        "is_arr": 0,
        "area_mismatch_pct": round(mismatch, 1),
        "flag_count": int(rng.integers(1, 4)),  # overclaim + mismatch type flags
        "label": label,
    }


def _gen_phantom_forest(rng: np.random.Generator) -> dict:
    """Phantom forest — company claims dense forest but NDVI shows bare ground → REJECTED"""
    claimed = rng.uniform(500, 3000)
    verified = claimed * rng.uniform(0.01, 0.15)
    overlap = (verified / claimed) * 100
    ndvi_curr = rng.uniform(0.03, 0.20)  # bare/sparse
    ndvi_hist = rng.uniform(0.05, 0.22)
    return {
        "overlap_percent": round(overlap, 1),
        "claimed_hectares": round(claimed, 1),
        "verified_hectares": round(verified, 1),
        "area_ratio": round(verified / claimed, 3),
        "protected_area_overlap_ha": 0.0,
        "ndvi_current_mean": round(ndvi_curr, 3),
        "ndvi_historical_mean": round(ndvi_hist, 3),
        "ndvi_change": round(ndvi_curr - ndvi_hist, 3),
        "ndvi_anomaly_score": round(rng.uniform(65, 100), 1),
        "additionality_score": round(rng.uniform(5, 30), 1),
        "is_arr": 0,
        "area_mismatch_pct": round(rng.uniform(50, 200), 1),
        "flag_count": int(rng.integers(1, 4)),  # CRITICAL overlap + fraud flags
        "label": "REJECTED",
    }


def _gen_protected_area(rng: np.random.Generator) -> dict:
    """Protected area laundering — good forest but inside a national park → REJECTED"""
    claimed = rng.uniform(300, 1200)
    overlap = rng.uniform(60, 95)
    verified = claimed * overlap / 100
    ndvi_curr = rng.uniform(0.60, 0.85)
    ndvi_hist = rng.uniform(0.58, 0.80)
    pa_overlap = claimed * rng.uniform(0.5, 0.95)  # significant PA overlap
    return {
        "overlap_percent": round(overlap, 1),
        "claimed_hectares": round(claimed, 1),
        "verified_hectares": round(verified, 1),
        "area_ratio": round(verified / claimed, 3),
        "protected_area_overlap_ha": round(pa_overlap, 1),
        "ndvi_current_mean": round(ndvi_curr, 3),
        "ndvi_historical_mean": round(ndvi_hist, 3),
        "ndvi_change": round(ndvi_curr - ndvi_hist, 3),
        "ndvi_anomaly_score": round(rng.uniform(10, 35), 1),
        "additionality_score": round(rng.uniform(20, 60), 1),
        "is_arr": 0,
        "area_mismatch_pct": round(rng.uniform(0, 15), 1),
        "flag_count": int(rng.integers(1, 3)),  # protected area flags
        "label": "REJECTED",
    }


def _gen_mixed_signals(rng: np.random.Generator) -> dict:
    """Mixed signals — some things look okay, others don't → CONDITIONALLY_VERIFIED or REQUIRES_REVIEW"""
    claimed = rng.uniform(300, 2000)
    overlap = rng.uniform(35, 70)
    verified = claimed * overlap / 100
    ndvi_curr = rng.uniform(0.35, 0.60)
    ndvi_hist = ndvi_curr + rng.uniform(-0.12, 0.05)
    mismatch = rng.uniform(10, 45)

    label = "CONDITIONALLY_VERIFIED" if overlap > 50 else "REQUIRES_REVIEW"

    return {
        "overlap_percent": round(overlap, 1),
        "claimed_hectares": round(claimed, 1),
        "verified_hectares": round(verified, 1),
        "area_ratio": round(verified / claimed, 3),
        "protected_area_overlap_ha": round(rng.uniform(0, 30), 1),
        "ndvi_current_mean": round(_clip(ndvi_curr, 0, 1), 3),
        "ndvi_historical_mean": round(_clip(ndvi_hist, 0, 1), 3),
        "ndvi_change": round(ndvi_curr - ndvi_hist, 3),
        "ndvi_anomaly_score": round(rng.uniform(20, 55), 1),
        "additionality_score": round(rng.uniform(35, 70), 1),
        "is_arr": int(rng.integers(0, 2)),
        "area_mismatch_pct": round(mismatch, 1),
        "flag_count": int(rng.integers(0, 2)),  # mixed signals, few serious flags
        "label": label,
    }


def _gen_declining_ndvi(rng: np.random.Generator) -> dict:
    """Moderate overlap but declining NDVI — something is wrong → REQUIRES_REVIEW or REJECTED"""
    claimed = rng.uniform(150, 800)
    overlap = rng.uniform(30, 65)
    verified = claimed * overlap / 100
    ndvi_hist = rng.uniform(0.45, 0.65)
    ndvi_decline = rng.uniform(0.05, 0.20)  # 5-20% decline
    ndvi_curr = ndvi_hist - ndvi_decline

    # Severe NDVI decline → REJECTED, moderate → REQUIRES_REVIEW
    label = "REJECTED" if ndvi_decline > 0.12 else "REQUIRES_REVIEW"

    return {
        "overlap_percent": round(overlap, 1),
        "claimed_hectares": round(claimed, 1),
        "verified_hectares": round(verified, 1),
        "area_ratio": round(verified / claimed, 3),
        "protected_area_overlap_ha": round(rng.uniform(0, 15), 1),
        "ndvi_current_mean": round(_clip(ndvi_curr, 0, 1), 3),
        "ndvi_historical_mean": round(ndvi_hist, 3),
        "ndvi_change": round(-ndvi_decline, 3),
        "ndvi_anomaly_score": round(rng.uniform(40, 80), 1),
        "additionality_score": round(rng.uniform(5, 35), 1),
        "is_arr": int(rng.integers(0, 2)),
        "area_mismatch_pct": round(rng.uniform(0, 30), 1),
        "flag_count": int(rng.integers(1, 3)),  # CRITICAL vegetation + mismatch
        "label": label,
    }


def _gen_moderate_data_gap(rng: np.random.Generator) -> dict:
    """Moderate overlap due to OSM data gaps, but NDVI shows real forest → CONDITIONALLY_VERIFIED"""
    claimed = rng.uniform(100, 600)
    overlap = rng.uniform(30, 60)  # moderate because OSM is incomplete
    verified = claimed * overlap / 100
    ndvi_curr = rng.uniform(0.45, 0.70)  # good vegetation despite low overlap
    ndvi_hist = ndvi_curr + rng.uniform(-0.05, 0.05)  # stable
    return {
        "overlap_percent": round(overlap, 1),
        "claimed_hectares": round(claimed, 1),
        "verified_hectares": round(verified, 1),
        "area_ratio": round(verified / claimed, 3),
        "protected_area_overlap_ha": 0.0,
        "ndvi_current_mean": round(_clip(ndvi_curr, 0, 1), 3),
        "ndvi_historical_mean": round(_clip(ndvi_hist, 0, 1), 3),
        "ndvi_change": round(ndvi_curr - ndvi_hist, 3),
        "ndvi_anomaly_score": round(rng.uniform(5, 25), 1),
        "additionality_score": round(rng.uniform(40, 75), 1),
        "is_arr": int(rng.integers(0, 2)),
        "area_mismatch_pct": round(rng.uniform(0, 15), 1),
        "flag_count": 0,  # OSM data gap, no serious flags
        "label": "CONDITIONALLY_VERIFIED",
    }


# ── Main generator ───────────────────────────────────────────────────────────

# Scenario weights control the class distribution
SCENARIO_GENERATORS = [
    (_gen_clean_redd, 0.16),           # 16% clean REDD+
    (_gen_clean_arr, 0.08),            #  8% clean ARR
    (_gen_mixed_signals, 0.18),        # 18% mixed/borderline
    (_gen_area_inflation, 0.14),       # 14% area inflation
    (_gen_phantom_forest, 0.12),       # 12% phantom forest
    (_gen_protected_area, 0.10),       # 10% protected area fraud
    (_gen_declining_ndvi, 0.12),       # 12% declining NDVI (NEW)
    (_gen_moderate_data_gap, 0.10),    # 10% moderate overlap but real forest (NEW)
]


def generate_dataset(n: int = 2000, seed: int = 42) -> pd.DataFrame:
    """
    Generate n synthetic training samples.

    Args:
        n: total number of samples
        seed: random seed for reproducibility

    Returns:
        DataFrame with FEATURE_COLS + 'label' column
    """
    rng = np.random.default_rng(seed)

    generators = [g for g, _ in SCENARIO_GENERATORS]
    weights = np.array([w for _, w in SCENARIO_GENERATORS])
    weights = weights / weights.sum()  # normalise

    rows = []
    for _ in range(n):
        idx = rng.choice(len(generators), p=weights)
        row = generators[idx](rng)
        rows.append(row)

    df = pd.DataFrame(rows)

    # Encode label as integer
    df["label_encoded"] = df["label"].map(LABELS)

    return df


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic training data")
    parser.add_argument("--n", type=int, default=2000, help="Number of samples")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    print(f"🔄 Generating {args.n} synthetic training samples (seed={args.seed})...")
    df = generate_dataset(n=args.n, seed=args.seed)

    # Save
    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "training_data.csv"
    df.to_csv(output_path, index=False)

    print(f"✅ Saved to {output_path}")
    print(f"   Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"\n📊 Class distribution:")
    print(df["label"].value_counts().to_string())
    print(f"\n📋 Feature columns: {FEATURE_COLS}")
    print(f"\n🔍 Sample row:")
    print(df.iloc[0].to_string())


if __name__ == "__main__":
    main()
