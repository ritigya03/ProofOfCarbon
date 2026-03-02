import sys
import os
from pathlib import Path
import logging

from dotenv import load_dotenv

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

load_dotenv()

from tools.satellite import fetch_ndvi_for_bbox

# Setup logging to see the output
logging.basicConfig(level=logging.INFO)

def test_ndvi():
    # Coorg forest area roughly
    bbox = {"min_lon": 75.7, "min_lat": 12.4, "max_lon": 75.8, "max_lat": 12.5}
    
    print("🛰️ Testing NDVI fetch...")
    result = fetch_ndvi_for_bbox(bbox)
    
    print("\n📊 Result:")
    print(f"Data Source: {result.get('data_source')}")
    print(f"NDVI Current: {result.get('ndvi_current_mean')}")
    print(f"NDVI Historical: {result.get('ndvi_historical_mean')}")
    print(f"Trend: {result.get('ndvi_trend')}")
    print(f"Flags: {result.get('flags')}")

if __name__ == "__main__":
    test_ndvi()
