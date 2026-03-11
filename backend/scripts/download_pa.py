"""
scripts/download_pa.py  — download India protected areas only
Uses a smaller, faster query.
Run from backend/:  python scripts/download_pa.py
"""
import json, requests, time
from pathlib import Path

OUT = Path(__file__).parent.parent / "data" / "reference" / "india_protected_areas.geojson"

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# Smaller query — only national parks & tiger reserves (not all protected_area)
QUERY = """
[out:geojson][timeout:180];
(
  relation["boundary"="national_park"](6.5,68.0,37.0,97.4);
  relation["boundary"="protected_area"]["protect_class"~"^[12]$"](6.5,68.0,37.0,97.4);
  relation["leisure"="nature_reserve"](6.5,68.0,37.0,97.4);
);
out geom;
"""

def download():
    for url in ENDPOINTS:
        print(f"Trying {url.split('/')[2]}...", end=" ", flush=True)
        try:
            r = requests.post(url, data={"data": QUERY}, timeout=200, stream=True)
            if r.status_code == 200:
                print("OK — saving...")
                with open(OUT, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                size = OUT.stat().st_size / 1024
                print(f"✅ Saved {size:.0f} KB → {OUT.name}")
                return True
            print(f"HTTP {r.status_code}")
        except Exception as e:
            print(f"error: {e}")
        time.sleep(5)
    return False

if __name__ == "__main__":
    print("Downloading India Protected Areas (national parks + nature reserves)")
    ok = download()
    if not ok:
        print("❌ Failed — keeping existing mock file")
