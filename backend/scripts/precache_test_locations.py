import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from tools.geospatial import load_reference

def precache():
    test_locations = [
        {"min_lon": 75.7, "min_lat": 12.35, "max_lon": 75.8, "max_lat": 12.45}, # Coorg REDD+
        {"min_lon": 77.7, "min_lat": 13.7,  "max_lon": 77.9, "max_lat": 13.9},  # Bagepalli ARR
        {"min_lon": 77.55, "min_lat": 12.95, "max_lon": 77.65, "max_lat": 13.0}, # Bangalore REDD Fail
        {"min_lon": 81.4, "min_lat": 17.4,  "max_lon": 81.5, "max_lat": 17.5},  # Andhra REDD
    ]

    print("🚀 Pre-caching forest cover reference data for test locations...")
    print("This involves on-demand Overpass API fetches for each AOI.\n")

    for i, bbox in enumerate(test_locations):
        print(f"[{i+1}/{len(test_locations)}] Fetching AOI: {bbox['min_lon']}, {bbox['min_lat']}...")
        try:
            # This triggers the Tier 2 Precision AOI Fetch and saves to data/reference/cache/
            gdf = load_reference(bbox)
            if not gdf.empty:
                print(f"  ✅ Cached {len(gdf)} reference polygons.")
            else:
                print(f"  ⚠️ No forest found in this AOI (Expected for some cases).")
        except Exception as e:
            print(f"  ❌ Failed: {e}")

    print("\n✨ Pre-caching complete. Test KMZs will now run instantly!")

if __name__ == "__main__":
    precache()
