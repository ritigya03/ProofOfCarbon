"""
tests/test_fraud_detection.py

Tests FraudDetectionAgent in isolation — no server needed.

Usage:
    python tests/test_fraud_detection.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

from agents.fraud_detection import FraudDetectionAgent

# ── Mock inputs simulating what main.py would pass in ─────────────────────────
# These represent the merged output of ProjectAnalysisAgent + SatelliteEvidenceAgent

SCENARIOS = [
    {
        "name": "✅ CLEAN CLAIM — should show low fraud signals",
        "input": {
            "project_name": "Kodagu Forest Conservation",
            "company_name": "GreenFuture Ltd",
            "state": "Karnataka",
            "forest_type": "Dense Evergreen",
            "claimed_hectares": 487.3,
            "verified_hectares": 421.8,
            "overlap_percent": 86.6,
            "protected_area_overlap_ha": 0.0,
            "risk_level": "LOW",
            "all_flags": [],
            "ndvi_current_mean": 0.72,
            "ndvi_historical_mean": 0.68,
            "ndvi_trend": "STABLE",
            "ndvi_anomaly_score": 5.0,
            "vegetation_class": "DENSE_FOREST",
            "satellite_risk_level": "LOW",
            "satellite_flags": [],
        },
        "expect_anomaly_below": 40,
        "expect_fraud_risk": ["LOW", "MEDIUM"],
    },
    {
        "name": "🚨 PHANTOM FOREST — NDVI contradicts forest claim",
        "input": {
            "project_name": "Rajasthan Dense Forest Project",
            "company_name": "CarbonMax Inc",
            "state": "Rajasthan",
            "forest_type": "Dense Forest",
            "claimed_hectares": 2000.0,  # suspiciously round number
            "verified_hectares": 87.3,
            "overlap_percent": 4.4,
            "protected_area_overlap_ha": 0.0,
            "risk_level": "CRITICAL",
            "all_flags": [
                "CRITICAL: Less than 10% of claimed area matches verified forest cover",
                "Area overclaim detected: 2000.0 ha claimed vs 87.3 ha verified",
            ],
            "ndvi_current_mean": 0.08,  # near bare ground
            "ndvi_historical_mean": 0.09,
            "ndvi_trend": "STABLE",
            "ndvi_anomaly_score": 78.0,
            "vegetation_class": "BARE_GROUND",
            "satellite_risk_level": "CRITICAL",
            "satellite_flags": [
                "CRITICAL: NDVI 0.08 — near bare ground, no forest possible",
                "Company claims NDVI > 0.6 but satellite shows 0.08",
            ],
        },
        "expect_anomaly_above": 60,
        "expect_fraud_risk": ["HIGH", "CRITICAL"],
    },
    {
        "name": "🔴 PROTECTED AREA LAUNDERING",
        "input": {
            "project_name": "Uttarakhand Forest Credits",
            "company_name": "TerraVerde",
            "state": "Uttarakhand",
            "forest_type": "Temperate Forest",
            "claimed_hectares": 800.0,
            "verified_hectares": 712.0,
            "overlap_percent": 89.0,
            "protected_area_overlap_ha": 650.0,  # mostly inside a national park
            "risk_level": "HIGH",
            "all_flags": [
                "Claimed area overlaps 650.0 ha of protected area: Jim Corbett National Park",
                "Land already under legal protection cannot generate new carbon credits",
            ],
            "ndvi_current_mean": 0.71,
            "ndvi_historical_mean": 0.69,
            "ndvi_trend": "STABLE",
            "ndvi_anomaly_score": 12.0,
            "vegetation_class": "DENSE_FOREST",
            "satellite_risk_level": "LOW",
            "satellite_flags": [],
        },
        "expect_anomaly_above": 50,
        "expect_fraud_risk": ["HIGH", "CRITICAL"],
    },
]


def run_test(scenario: dict, agent: FraudDetectionAgent) -> bool:
    print(f"\n{'─'*60}")
    print(f"Scenario: {scenario['name']}")
    print(f"{'─'*60}")

    result = agent.run(combined_data=scenario["input"])

    print(f"  Anomaly Score:    {result.get('anomaly_score')}/100")
    print(f"  Fraud Risk:       {result.get('fraud_risk_level')}")
    print(f"  Fraud Patterns:")
    for pattern, status in result.get("fraud_patterns", {}).items():
        icon = "🔴" if status in ("CONFIRMED", "SUSPECTED") else "✅"
        print(f"    {icon} {pattern}: {status}")
    print(f"  Fraud Flags:")
    for flag in result.get("fraud_flags", []):
        print(f"    • {flag}")
    print(f"  Summary: {result.get('fraud_summary')}")

    passed = True

    if "expect_anomaly_above" in scenario:
        threshold = scenario["expect_anomaly_above"]
        score = result.get("anomaly_score", 0)
        if score < threshold:
            print(f"  ⚠️  Expected anomaly_score > {threshold}, got {score}")
            passed = False

    if "expect_anomaly_below" in scenario:
        threshold = scenario["expect_anomaly_below"]
        score = result.get("anomaly_score", 100)
        if score >= threshold:
            print(f"  ⚠️  Expected anomaly_score < {threshold}, got {score}")
            passed = False

    if "expect_fraud_risk" in scenario:
        expected = scenario["expect_fraud_risk"]
        got = result.get("fraud_risk_level")
        if got not in expected:
            print(f"  ⚠️  Expected fraud_risk in {expected}, got {got}")
            passed = False

    print(f"  {'✅ PASSED' if passed else '❌ FAILED'}")
    return passed


def main():
    print("Initializing FraudDetectionAgent...")
    agent = FraudDetectionAgent()
    print("Agent ready.\n")

    results = [run_test(s, agent) for s in SCENARIOS]
    passed = sum(results)
    total = len(results)

    print(f"\n{'='*60}")
    print(f"FraudDetectionAgent: {passed}/{total} scenarios passed")
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some scenarios had unexpected results")


if __name__ == "__main__":
    main()
