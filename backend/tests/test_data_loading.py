import sys, os
sys.path.insert(0, os.path.abspath("."))

print("=== Test 1: baseline CSV loading ===")
from tools.baseline import compute_additionality_metrics
r = compute_additionality_metrics("Karnataka", "dense", 500)
print(f"  additionality_score:    {r['additionality_score']}")
print(f"  deforestation_pressure: {r['deforestation_pressure']}")
print(f"  data_source:            {r['data_source']}")
print(f"  primary_drivers:        {r['primary_drivers']}")
assert r["additionality_score"] == 1.9, f"Expected 1.9, got {r['additionality_score']}"
assert r["deforestation_pressure"] == "MEDIUM"
assert "mock" not in r["data_source"].lower(), "data_source should not say mock"
print("  ✅ PASSED\n")

print("=== Test 2: default fallback state ===")
r2 = compute_additionality_metrics("UnknownState", "dense", 500)
print(f"  state:    {r2['state']}")
print(f"  pressure: {r2['deforestation_pressure']}")
assert r2["deforestation_pressure"] == "MEDIUM"
print("  ✅ PASSED\n")

print("=== Test 3: satellite thresholds JSON loading ===")
from tools.satellite import NDVI_DENSE_FOREST, NDVI_DEGRADED, NDVI_BARE, TREND_DROP_PCT
print(f"  NDVI_DENSE_FOREST: {NDVI_DENSE_FOREST}")
print(f"  NDVI_DEGRADED:     {NDVI_DEGRADED}")
print(f"  NDVI_BARE:         {NDVI_BARE}")
print(f"  TREND_DROP_PCT:    {TREND_DROP_PCT}")
assert NDVI_DENSE_FOREST == 0.50
assert NDVI_DEGRADED == 0.30
assert NDVI_BARE == 0.10
print("  ✅ PASSED\n")

print("=== Test 4: satellite mock fetch ===")
from tools.satellite import fetch_ndvi_for_bbox
r3 = fetch_ndvi_for_bbox({"min_lon": 75.0, "min_lat": 12.0, "max_lon": 76.0, "max_lat": 13.0})
print(f"  data_source:       {r3['data_source']}")
print(f"  ndvi_current_mean: {r3['ndvi_current_mean']}")
assert r3["data_source"] == "MOCK"
assert 0.0 <= r3["ndvi_current_mean"] <= 1.0
print("  ✅ PASSED\n")

print("=== Test 5: Manipur (CRITICAL pressure) ===")
r4 = compute_additionality_metrics("Manipur", "dense", 1000)
print(f"  pressure: {r4['deforestation_pressure']}")
print(f"  flags:    {r4['baseline_flags']}")
assert r4["deforestation_pressure"] == "CRITICAL"
print("  ✅ PASSED\n")

print("🎉 All smoke tests passed!")
