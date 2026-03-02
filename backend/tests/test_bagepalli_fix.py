import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))
load_dotenv()

from agents.project_analysis import ProjectAnalysisAgent
from agents.satellite_evidence import SatelliteEvidenceAgent
from agents.historical_baseline import HistoricalBaselineAgent
from agents.fraud_detection import FraudDetectionAgent
from agents.verifier import VerifierAgent

def test_arr_bagepalli_scenario():
    print("\n🔍 Testing ARR Bagepalli Scenario (0% overlap, valid KMZ)...")
    
    # 1. Project Analysis (Spatial)
    # Simulate a result where overlap is 0 but it's clearly ARR
    spatial_result = {
        "project_name": "Bagepalli Reforestation",
        "company_name": "GreenLife India",
        "project_type": "ARR",
        "state": "Karnataka",
        "forest_type": "Native Broadleaf",
        "claimed_area_ha": 5870.6,
        "verified_area_ha": 0.0,
        "overlap_percent": 0.0,
        "risk_level": "LOW", # Should be LOW for ARR even with 0% overlap
        "trust_score": 85,
        "all_flags": ["No forest overlap - expected for ARR start"],
        "bbox": {"min_lon": 77.0, "min_lat": 13.0, "max_lon": 78.0, "max_lat": 14.0},
        "text_claimed_ha": 5870.6,
        "area_mismatch_pct": 0.0
    }
    
    # 2. Satellite Evidence
    # NDVI 0.44 is moderate, stable trend is neutral
    sat_result = {
        "vegetation_class": "MODERATE_FOREST",
        "satellite_risk_level": "LOW",
        "satellite_trust_modifier": 0,
        "satellite_flags": ["NDVI 0.44 - moderate vegetation; partial or degraded forest"],
        "satellite_summary": "Moderate NDVI, stable trend.",
        "ndvi_current_mean": 0.4383,
        "ndvi_historical_mean": 0.4362,
        "ndvi_trend": "STABLE",
        "ndvi_anomaly_score": 0.5,
        "pixel_count": 1200,
        "data_source": "MODIS_MOCK"
    }
    
    # 3. Baseline Analysis (Additionality)
    # Karnataka has MEDIUM pressure.
    from tools.baseline import compute_additionality_metrics
    baseline_metrics = compute_additionality_metrics(
        state="Karnataka",
        forest_type="Native Broadleaf",
        claimed_ha=5870.6,
        project_type="ARR"
    )
    
    agent_baseline = HistoricalBaselineAgent()
    # Mocking the baseline agent's run with data we calculated
    baseline_result = {
        **baseline_metrics,
        "additionality_verdict": "STRONG",
        "baseline_summary": "Strong additionality due to low natural regeneration in Karnataka.",
        "permanence_assessment": "Moderate permanence risk.",
        "counterfactual_assessment": "Land would remain degraded scrub."
    }
    
    # 4. Fraud Detection
    # This is where it failed before. Let's see if the fix works.
    fraud_agent = FraudDetectionAgent()
    combined_for_fraud = {**spatial_result, **sat_result, **baseline_result}
    fraud_result = fraud_agent.run(combined_for_fraud)
    
    print(f"Fraud Risk Level: {fraud_result['fraud_risk_level']}")
    print(f"Anomaly Score: {fraud_result['anomaly_score']}")
    print(f"Area Inflation Pattern: {fraud_result['fraud_patterns'].get('area_inflation')}")
    print(f"Fraud Summary: {fraud_result['fraud_summary']}")
    
    # 5. Verifier
    verifier = VerifierAgent()
    final_combined = {**combined_for_fraud, **fraud_result}
    final_result = verifier.run(final_combined)
    
    print("\n✅ Final Verdict:")
    print(f"Verdict: {final_result['final_verdict']}")
    print(f"Trust Score: {final_result['final_trust_score']}")
    print(f"Summary: {final_result['verification_summary']}")

if __name__ == "__main__":
    test_arr_bagepalli_scenario()
