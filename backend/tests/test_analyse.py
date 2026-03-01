"""
tests/test_analyze.py

Full end-to-end integration test — runs all 4 KMZ scenarios through the
complete /analyze pipeline (all 4 agents).

Usage:
    # Terminal 1 — start server:
    uvicorn api.main:app --reload --port 8000

    # Terminal 2 — run tests:
    python tests/test_analyze.py
"""

import sys
import requests

BASE_URL = "http://localhost:8000"

SCENARIOS = [
    {
        "name": "✅ VALID CLAIM",
        "kmz": "data/sample_claims/valid_claim.kmz",
        "claim": "GreenFuture Ltd — 500 ha forest conservation in Kodagu, Karnataka. Dense evergreen forest.",
        # Stage 1 — spatial
        "expect_risk": ["LOW", "MEDIUM"],
        "expect_trust_above": 50,
        # Stage 2 — satellite
        "expect_vegetation_class": ["DENSE_FOREST", "MODERATE_FOREST"],
        # Stage 3 — fraud
        "expect_anomaly_below": 50,
        # Stage 4 — verifier
        "expect_verdict": ["VERIFIED", "CONDITIONALLY_VERIFIED"],
    },
    {
        "name": "⚠️  PARTIAL CLAIM",
        "kmz": "data/sample_claims/partial_claim.kmz",
        "claim": "EcoBalance Corp — 1200 ha reforestation in Karnataka-Kerala border.",
        "expect_risk": ["MEDIUM", "HIGH"],
        "expect_trust_above": 10,
        "expect_vegetation_class": [
            "MODERATE_FOREST",
            "DENSE_FOREST",
            "SPARSE_VEGETATION",
        ],
        "expect_anomaly_below": 75,
        "expect_verdict": ["CONDITIONALLY_VERIFIED", "REQUIRES_REVIEW"],
    },
    {
        "name": "🚨 INVALID CLAIM",
        "kmz": "data/sample_claims/invalid_claim.kmz",
        "claim": "CarbonMax Inc — 2000 ha dense forest in Rajasthan. Claims pristine forest with NDVI > 0.6.",
        "expect_risk": ["HIGH", "CRITICAL"],
        "expect_trust_above": 0,
        "expect_vegetation_class": ["SPARSE_VEGETATION", "DEGRADED", "BARE_GROUND"],
        "expect_anomaly_above": 50,
        "expect_verdict": ["REJECTED", "REQUIRES_REVIEW"],
    },
    {
        "name": "🔴 PROTECTED AREA OVERLAP",
        "kmz": "data/sample_claims/protected_overlap_claim.kmz",
        "claim": "TerraVerde — 800 ha forest project in Uttarakhand near Corbett.",
        "expect_risk": ["HIGH", "CRITICAL"],
        "expect_trust_above": 0,
        "expect_vegetation_class": None,  # any — the PA violation is the key signal
        "expect_anomaly_above": 40,
        "expect_verdict": ["REJECTED", "REQUIRES_REVIEW"],
    },
]


def print_section(title: str):
    print(f"\n  ── {title} {'─' * (50 - len(title))}")


def run_test(scenario: dict) -> bool:
    print(f"\n{'━'*62}")
    print(f"  {scenario['name']}")
    print(f"{'━'*62}")

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
            timeout=120,
        )

    if response.status_code != 200:
        print(f"  ❌ HTTP {response.status_code}: {response.text[:300]}")
        return False

    r = response.json()
    passed = True

    # ── Stage 1: Spatial ─────────────────────────────────────────────────────
    print_section("Stage 1 — Spatial Analysis")
    print(f"  Project:        {r.get('project_name')} / {r.get('company_name')}")
    print(f"  State:          {r.get('state')}")
    print(f"  Claimed:        {r.get('claimed_hectares')} ha")
    print(f"  Verified:       {r.get('verified_hectares')} ha")
    print(f"  Overlap:        {r.get('overlap_percent')}%")
    print(f"  PA Overlap:     {r.get('protected_area_overlap_ha')} ha")
    print(f"  Spatial Risk:   {r.get('risk_level')}")
    print(f"  Trust (so far): {r.get('trust_score')}")

    if r.get("risk_level") not in scenario["expect_risk"]:
        print(
            f"  ⚠️  Expected risk in {scenario['expect_risk']}, got {r.get('risk_level')}"
        )
        passed = False
    if r.get("trust_score", 0) < scenario["expect_trust_above"]:
        print(
            f"  ⚠️  Expected trust > {scenario['expect_trust_above']}, got {r.get('trust_score')}"
        )
        passed = False

    # ── Stage 2: Satellite ───────────────────────────────────────────────────
    print_section("Stage 2 — Satellite Evidence")
    print(f"  NDVI Current:   {r.get('ndvi_current_mean')}")
    print(f"  NDVI Trend:     {r.get('ndvi_trend')}")
    print(f"  Vegetation:     {r.get('vegetation_class')}")
    print(f"  Satellite Risk: {r.get('satellite_risk_level')}")
    print(f"  Trust Modifier: {r.get('satellite_trust_modifier')}")
    print(f"  Satellite Summary: {r.get('satellite_summary')}")

    expected_veg = scenario.get("expect_vegetation_class")
    if expected_veg and r.get("vegetation_class") not in expected_veg:
        print(
            f"  ⚠️  Expected vegetation in {expected_veg}, got {r.get('vegetation_class')}"
        )
        passed = False

    # ── Stage 3: Fraud Detection ─────────────────────────────────────────────
    print_section("Stage 3 — Fraud Detection")
    print(f"  Anomaly Score:  {r.get('anomaly_score')}/100")
    print(f"  Fraud Risk:     {r.get('fraud_risk_level')}")
    patterns = r.get("fraud_patterns") or {}
    for k, v in patterns.items():
        icon = "🔴" if v in ("CONFIRMED", "SUSPECTED") else "✅"
        print(f"    {icon} {k}: {v}")
    print(f"  Fraud Summary:  {r.get('fraud_summary')}")

    if "expect_anomaly_above" in scenario:
        threshold = scenario["expect_anomaly_above"]
        score = r.get("anomaly_score") or 0
        if score < threshold:
            print(f"  ⚠️  Expected anomaly > {threshold}, got {score}")
            passed = False
    if "expect_anomaly_below" in scenario:
        threshold = scenario["expect_anomaly_below"]
        score = r.get("anomaly_score") or 0
        if score >= threshold:
            print(f"  ⚠️  Expected anomaly < {threshold}, got {score}")
            passed = False

    # ── Stage 4: Final Verdict ───────────────────────────────────────────────
    print_section("Stage 4 — Final Verdict")
    print(f"  Verdict:        {r.get('final_verdict')}")
    print(f"  Final Trust:    {r.get('final_trust_score')}/100")
    print(f"  Confidence:     {r.get('confidence')}")
    print(f"  Recommendation: {r.get('recommendation')}")
    for finding in r.get("key_findings", []):
        print(f"    • {finding}")
    print(f"  Summary: {r.get('verification_summary')}")

    if r.get("final_verdict") not in scenario["expect_verdict"]:
        print(
            f"  ⚠️  Expected verdict in {scenario['expect_verdict']}, got {r.get('final_verdict')}"
        )
        passed = False

    # ── All Flags ────────────────────────────────────────────────────────────
    all_flags = r.get("all_flags", [])
    if all_flags:
        print_section("All Flags")
        for flag in all_flags:
            print(f"    • {flag}")

    print(f"\n  {'✅ PASSED' if passed else '❌ FAILED'}")
    return passed


def main():
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        health = r.json()
        print(f"Server health: {health}")
        if not health.get("agent_ready"):
            print("❌ Agents not ready — check server startup logs")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Server not reachable at {BASE_URL}: {e}")
        print("   Run: uvicorn api.main:app --reload --port 8000")
        sys.exit(1)

    results = [run_test(s) for s in SCENARIOS]
    passed = sum(results)
    total = len(results)

    print(f"\n{'='*62}")
    print(f"Final Results: {passed}/{total} scenarios passed")
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some scenarios had unexpected results — review above")
        sys.exit(1)


if __name__ == "__main__":
    main()
