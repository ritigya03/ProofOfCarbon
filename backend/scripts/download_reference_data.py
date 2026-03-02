"""
scripts/download_reference_data.py
===================================
Downloads real India forest cover and protected area GeoJSON from OpenStreetMap.
Uses a single bulk query per dataset — faster and avoids per-state rate limits.

Run from backend/ directory:
    python scripts/download_reference_data.py
"""

import json, os, sys, time, requests
from pathlib import Path

OUT_DIR    = Path(__file__).parent.parent / "data" / "reference"
FOREST_OUT = OUT_DIR / "india_forest_cover.geojson"
PA_OUT     = OUT_DIR / "india_protected_areas.geojson"

# Use multiple Overpass endpoints for fallback
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

INDIA_BBOX = "6.5,68.0,37.0,97.4"   # south,west,north,east


def post_overpass(query: str, timeout_s: int = 240) -> dict | None:
    """Try each Overpass endpoint until one succeeds."""
    for url in ENDPOINTS:
        try:
            print(f"  Trying {url.split('/')[2]}...", end=" ", flush=True)
            r = requests.post(url, data={"data": query}, timeout=timeout_s)
            if r.status_code == 200:
                print("OK")
                return r.json()
            print(f"HTTP {r.status_code}")
        except requests.exceptions.Timeout:
            print("timeout")
        except Exception as e:
            print(f"error: {e}")
        time.sleep(3)
    return None


def elements_to_features(elements: list, props_fn) -> list:
    """Convert Overpass way/relation elements to GeoJSON features."""
    features = []
    for el in elements:
        props = props_fn(el)
        geom  = None

        if el.get("type") == "way" and "geometry" in el:
            coords = [[pt["lon"], pt["lat"]] for pt in el["geometry"]]
            if len(coords) >= 4:
                geom = {"type": "Polygon", "coordinates": [coords]}

        elif el.get("type") == "relation" and "members" in el:
            outers = [
                m for m in el["members"]
                if m.get("role") == "outer" and "geometry" in m
            ]
            if outers:
                rings = []
                for o in outers:
                    coords = [[pt["lon"], pt["lat"]] for pt in o["geometry"]]
                    if len(coords) >= 4:
                        rings.append(coords)
                if rings:
                    geom = {
                        "type": "MultiPolygon" if len(rings) > 1 else "Polygon",
                        "coordinates": rings if len(rings) > 1 else rings[0] if len(rings) == 1 else [],
                    }
                    if geom["type"] == "MultiPolygon":
                        geom["coordinates"] = [[r] for r in rings]

        if geom:
            features.append({"type": "Feature", "properties": props, "geometry": geom})

    return features


def download_forest():
    print("\n=== Forest Cover (OSM landuse=forest + natural=wood) ===")
    # Single query covering all of India — much faster than per-state
    query = f"""
[out:json][timeout:240];
(
  way["landuse"="forest"]({INDIA_BBOX});
  way["natural"="wood"]({INDIA_BBOX});
  relation["landuse"="forest"][type="multipolygon"]({INDIA_BBOX});
  relation["natural"="wood"][type="multipolygon"]({INDIA_BBOX});
);
out geom;
"""
    data = post_overpass(query, timeout_s=250)
    if not data:
        print("❌ All endpoints failed. Check internet connection.")
        return 0

    elements = data.get("elements", [])
    print(f"  Got {len(elements)} raw elements")

    def forest_props(el):
        tags = el.get("tags", {})
        return {
            "id":          el.get("id"),
            "name":        tags.get("name", ""),
            "forest_type": tags.get("landuse") or tags.get("natural", "forest"),
        }

    features = elements_to_features(elements, forest_props)
    _save(FOREST_OUT, "india_forest_cover", features)
    return len(features)


def download_pa():
    print("\n=== Protected Areas (national parks, sanctuaries, tiger reserves) ===")
    query = f"""
[out:json][timeout:240];
(
  relation["boundary"="protected_area"]({INDIA_BBOX});
  relation["boundary"="national_park"]({INDIA_BBOX});
  relation["leisure"="nature_reserve"]({INDIA_BBOX});
  way["boundary"="protected_area"]({INDIA_BBOX});
  way["leisure"="nature_reserve"]({INDIA_BBOX});
);
out geom;
"""
    data = post_overpass(query, timeout_s=250)
    if not data:
        print("❌ All endpoints failed.")
        return 0

    elements = data.get("elements", [])
    print(f"  Got {len(elements)} raw elements")

    def pa_props(el):
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:en", "")
        return {
            "id":   el.get("id"),
            "name": name,
            "NAME": name,
            "type": tags.get("boundary") or tags.get("leisure", "protected_area"),
        }

    features = elements_to_features(elements, pa_props)
    _save(PA_OUT, "india_protected_areas", features)
    return len(features)


def _save(path: Path, name: str, features: list):
    geojson = {
        "type": "FeatureCollection",
        "name": name,
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(geojson, f)
    size_mb = path.stat().st_size / 1024 / 1024
    print(f"  ✅ Saved {len(features)} polygons → {path.name}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    print("ProofOfCarbon — Reference Data Downloader v2 (bulk query)")
    print("==========================================================")
    print("Downloading all of India in one query per dataset.")
    print("This may take 2-4 minutes — do not interrupt.\n")

    f_count = download_forest()
    p_count = download_pa()

    print(f"\n========================================")
    if f_count > 0 or p_count > 0:
        print(f"✅ Done!  Forest: {f_count} polygons  |  Protected: {p_count} polygons")
        print("Restart uvicorn now:")
        print("  uvicorn api.main:app --reload --port 8000")
    else:
        print("❌ Download failed — check internet and try again.")
    print("========================================")
