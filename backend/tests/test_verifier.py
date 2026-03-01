"""
tests/test_verifier.py

Tests VerifierAgent in isolation — no server needed.

Usage:
    python tests/test_verifier.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

from agents.verifier import VerifierAgent

SCENARIOS = [
    {
        "name": "✅ SHOULD BE VERIFIED — all signals clean",
        "input": {
            "project_name": "Kodagu Forest Conservation",
            "company_name": "GreenFuture Ltd",
            "state": "Karnataka",
            # Spatial
            "overlap_percent": 86.6,
            "claimed_hectares": 487.3,
            "verified_hectares": 421.8,
            "protected_area_overlap_ha": 0.0,
            "risk_level": "LOW",
            # Satellite
            "ndvi_current_mean": 0.72,
            "ndvi_trend": "STABLE",
            "vegetation_class": "DENSE_FOREST",
            "satellite_risk_level": "LOW",
            "satellite_trust_modifier": 8,
            # Fraud
            "anomaly_score": 12,
            "fraud_risk_level": "LOW",
            "fraud_patterns": {
                "phantom_forest": "CLEAR",
                "area_inflation": "CLEAR",
                "signal_contradiction": "CLEAR",
                "protected_area_laundering": "CLEAR",
                "round_number_anomaly": "CLEAR",
                "administrative_mismatch": "CLEAR",
            },
            "fraud_flags": [],
            # Intermediate
            "trust_score": 82.0,
            "all_flags": [],
        },
        "expect_verdict": ["VERIFIED", "CONDITIONALLY_VERIFIED"],
        "expect_trust_above": 65,
    },
    {
        "name": "⚠️  SHOULD REQUIRE REVIEW — mixed signals",
        "input": {
            "project_name": "Karnataka Border Reforestation",
            "company_name": "EcoBalance Corp",
            "state": "Karnataka",
            "overlap_percent": 41.0,
            "claimed_hectares": 1200.0,
            "verified_hectares": 492.0,
            "protected_area_overlap_ha": 0.0,
            "risk_level": "HIGH",
            "ndvi_current_mean": 0.48,
            "ndvi_trend": "STABLE",
            "vegetation_class": "MODERATE_FOREST",
            "satellite_risk_level": "MEDIUM",
            "satellite_trust_modifier": -5,
            "anomaly_score": 45,
            "fraud_risk_level": "MEDIUM",
            "fraud_patterns": {
                "phantom_forest": "CLEAR",
                "area_inflation": "SUSPECTED",
                "signal_contradiction": "POSSIBLE",
                "protected_area_laundering": "CLEAR",
                "round_number_anomaly": "SUSPECTED",
                "administrative_mismatch": "CLEAR",
            },
            "fraud_flags": [
                "Area inflation suspected: 1200 ha claimed vs 492 ha verified"
            ],
            "trust_score": 42.0,
            "all_flags": [
                "WARNING: Only 41.0% of claimed area is verified forest",
                "Area overclaim detected: 1200 ha claimed vs 492 ha verified",
            ],
        },
        "expect_verdict": ["REQUIRES_REVIEW", "CONDITIONALLY_VERIFIED"],
        "expect_trust_above": 0,
    },
    {
        "name": "🚨 SHOULD BE REJECTED — phantom forest + fraud",
        "input": {
            "project_name": "Rajasthan Dense Forest Project",
            "company_name": "CarbonMax Inc",
            "state": "Rajasthan",
            "overlap_percent": 4.4,
            "claimed_hectares": 2000.0,
            "verified_hectares": 87.3,
            "protected_area_overlap_ha": 0.0,
            "risk_level": "CRITICAL",
            "ndvi_current_mean": 0.08,
            "ndvi_trend": "STABLE",
            "vegetation_class": "BARE_GROUND",
            "satellite_risk_level": "CRITICAL",
            "satellite_trust_modifier": -30,
            "anomaly_score": 88,
            "fraud_risk_level": "CRITICAL",
            "fraud_patterns": {
                "phantom_forest": "CONFIRMED",
                "area_inflation": "CONFIRMED",
                "signal_contradiction": "CONFIRMED",
                "protected_area_laundering": "CLEAR",
                "round_number_anomaly": "SUSPECTED",
                "administrative_mismatch": "POSSIBLE",
            },
            "fraud_flags": [
                "CONFIRMED phantom forest: NDVI 0.08 with dense forest claim",
                "CONFIRMED area inflation: 23x overclaim detected",
            ],
            "trust_score": 8.0,
            "all_flags": [
                "CRITICAL: Less than 10% of claimed area matches verified forest",
                "CRITICAL: NDVI 0.08 — near bare ground",
                "CONFIRMED phantom forest: NDVI 0.08 with dense forest claim",
            ],
        },
        "expect_verdict": ["REJECTED"],
        "expect_trust_above": 0,
    },
]


def run_test(scenario: dict, agent: VerifierAgent) -> bool:
    print(f"\n{'─'*60}")
    print(f"Scenario: {scenario['name']}")
    print(f"{'─'*60}")

    result = agent.run(combined_data=scenario["input"])

    print(f"  Final Verdict:     {result.get('final_verdict')}")
    print(f"  Final Trust Score: {result.get('final_trust_score')}/100")
    print(f"  Final Risk Level:  {result.get('final_risk_level')}")
    print(f"  Confidence:        {result.get('confidence')}")
    print(f"  Key Findings:")
    for finding in result.get("key_findings", []):
        print(f"    • {finding}")
    print(f"  Recommendation: {result.get('recommendation')}")
    print(f"  Summary: {result.get('verification_summary')}")

    passed = True

    expected_verdicts = scenario.get("expect_verdict", [])
    got_verdict = result.get("final_verdict")
    if got_verdict not in expected_verdicts:
        print(f"  ⚠️  Expected verdict in {expected_verdicts}, got {got_verdict}")
        passed = False

    trust = result.get("final_trust_score", 0)
    min_trust = scenario.get("expect_trust_above", 0)
    if trust < min_trust:
        print(f"  ⚠️  Expected trust > {min_trust}, got {trust}")
        passed = False

    print(f"  {'✅ PASSED' if passed else '❌ FAILED'}")
    return passed


def main():
    print("Initializing VerifierAgent...")
    agent = VerifierAgent()
    print("Agent ready.\n")

    results = [run_test(s, agent) for s in SCENARIOS]
    passed = sum(results)
    total = len(results)

    print(f"\n{'='*60}")
    print(f"VerifierAgent: {passed}/{total} scenarios passed")
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some scenarios had unexpected results")


if __name__ == "__main__":
    main()
