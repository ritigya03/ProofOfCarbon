"""
tests/test_analyze.py

Run all 4 mock scenarios against the /analyze endpoint.
Usage:
    # Start server first:
    uvicorn api.main:app --reload --port 8000

    # Then in another terminal:
    python tests/test_analyze.py
"""

import sys
import requests
import json

BASE_URL = "http://localhost:8000"

SCENARIOS = [
    {
        "name": "✅ VALID CLAIM (should score HIGH trust)",
        "kmz": "data/sample_claims/valid_claim.kmz",
        "claim": "GreenFuture Ltd — 700 ha forest conservation in Kodagu, Karnataka. Dense evergreen forest.",
        "expect_risk": ["LOW", "MEDIUM"],
        "expect_trust_above": 50,
    },
    {
        "name": "⚠️  PARTIAL CLAIM (should score MEDIUM trust)",
        "kmz": "data/sample_claims/partial_claim.kmz",
        "claim": "EcoBalance Corp — 1200 ha reforestation project in Karnataka-Kerala border.",
        "expect_risk": ["MEDIUM", "HIGH"],
        "expect_trust_above": 20,
    },
    {
        "name": "🚨 INVALID CLAIM (should score CRITICAL/LOW trust)",
        "kmz": "data/sample_claims/invalid_claim.kmz",
        "claim": "CarbonMax Inc — 2000 ha dense forest in Rajasthan. Claims pristine forest with NDVI > 0.6.",
        "expect_risk": ["HIGH", "CRITICAL"],
        "expect_trust_above": 0,
    },
    {
        "name": "🔴 PROTECTED AREA OVERLAP (should be flagged)",
        "kmz": "data/sample_claims/protected_overlap_claim.kmz",
        "claim": "TerraVerde — 800 ha forest project in Uttarakhand near Corbett.",
        "expect_risk": ["HIGH", "CRITICAL"],
        "expect_trust_above": 0,
    },
]


def run_test(scenario: dict) -> bool:
    print(f"\n{'─'*60}")
    print(f"Scenario: {scenario['name']}")
    print(f"{'─'*60}")

    with open(scenario["kmz"], "rb") as f:
        response = requests.post(
            f"{BASE_URL}/analyze",
            files={
                "kmz_file": (
                    scenario["kmz"].split("/")[-1],
                    f,
                    "application/octet-stream",
                )
            },
            data={"company_claim": scenario["claim"]},
            timeout=60,
        )

    if response.status_code != 200:
        print(f"  ❌ HTTP {response.status_code}: {response.text}")
        return False

    result = response.json()

    print(f"  Project:       {result.get('project_name')}")
    print(f"  State:         {result.get('state')}")
    print(f"  Claimed:       {result.get('claimed_hectares')} ha")
    print(f"  Verified:      {result.get('verified_hectares')} ha")
    print(f"  Overlap:       {result.get('overlap_percent')}%")
    print(f"  PA Overlap:    {result.get('protected_area_overlap_ha')} ha")
    print(f"  Risk Level:    {result.get('risk_level')}")
    print(f"  Trust Score:   {result.get('trust_score')}/100")
    print(f"  Flags:")
    for flag in result.get("all_flags", []):
        print(f"    • {flag}")
    print(f"  Summary: {result.get('summary')}")

    # Basic assertions
    passed = True
    risk = result.get("risk_level")
    trust = result.get("trust_score", 0)

    if risk not in scenario["expect_risk"]:
        print(f"  ⚠️  Expected risk in {scenario['expect_risk']}, got {risk}")
        passed = False

    if trust < scenario["expect_trust_above"]:
        print(f"  ⚠️  Expected trust > {scenario['expect_trust_above']}, got {trust}")
        passed = False

    print(f"  {'✅ PASSED' if passed else '❌ FAILED'}")
    return passed


def main():
    # Health check first
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Server health: {r.json()}")
    except Exception as e:
        print(f"❌ Server not reachable at {BASE_URL}: {e}")
        print("   Run: uvicorn api.main:app --reload --port 8000")
        sys.exit(1)

    results = [run_test(s) for s in SCENARIOS]
    passed = sum(results)
    total = len(results)

    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} scenarios passed")
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some scenarios had unexpected results — review above")


if __name__ == "__main__":
    main()
