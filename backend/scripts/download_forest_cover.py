"""
scripts/download_forest_cover.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Download India forest cover data from OpenStreetMap via Overpass API.

Saves result to data/reference/india_forest_cover.geojson

Run from backend/:
    python scripts/download_forest_cover.py

Options:
    --state <name>   Only download forest for one Indian state (faster, e.g. Karnataka)
    --bbox <W,S,E,N> Custom bounding box (lon_min,lat_min,lon_max,lat_max)

The downloaded file is always written atomically to avoid leaving a corrupt
file behind if the download is interrupted.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

OUT = (
    Path(__file__).parent.parent / "data" / "reference" / "india_forest_cover.geojson"
)
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# Bounding boxes for common states (W, S, E, N)
STATE_BBOXES = {
    "karnataka":    (74.0, 11.5, 78.6, 18.5),
    "kerala":       (74.9, 8.2,  77.4, 12.8),
    "tamil_nadu":   (76.2, 8.0,  80.3, 13.6),
    "maharashtra":  (72.6, 15.6, 80.9, 22.0),
    "madhya_pradesh": (74.0, 21.0, 82.8, 26.9),
    "odisha":       (81.4, 17.8, 87.5, 22.6),
    "assam":        (89.7, 24.1, 96.0, 28.2),
    "india":        (68.0, 6.5,  97.4, 37.0),
}


def build_query(bbox: tuple) -> str:
    w, s, e, n = bbox
    return f"""
[out:json][timeout:300];
(
  way["natural"="wood"]({s},{w},{n},{e});
  way["landuse"="forest"]({s},{w},{n},{e});
  relation["natural"="wood"]({s},{w},{n},{e});
  relation["landuse"="forest"]({s},{w},{n},{e});
);
out geom;
"""


def overpass_to_geojson(data: dict) -> dict:
    """Convert Overpass JSON to a valid GeoJSON FeatureCollection."""
    features = []
    for elem in data.get("elements", []):
        coords = None
        geom_type = None

        if elem["type"] == "way" and "geometry" in elem:
            pts = [[pt["lon"], pt["lat"]] for pt in elem["geometry"]]
            if pts and pts[0] != pts[-1]:
                pts.append(pts[0])
            if len(pts) >= 4:
                coords = [pts]
                geom_type = "Polygon"

        elif elem["type"] == "relation" and "members" in elem:
            outer_rings = []
            for m in elem.get("members", []):
                if m.get("role") == "outer" and m.get("type") == "way" and "geometry" in m:
                    pts = [[pt["lon"], pt["lat"]] for pt in m["geometry"]]
                    if pts and pts[0] != pts[-1]:
                        pts.append(pts[0])
                    if len(pts) >= 4:
                        outer_rings.append(pts)
            if outer_rings:
                geom_type = "MultiPolygon" if len(outer_rings) > 1 else "Polygon"
                coords = [[r] for r in outer_rings] if len(outer_rings) > 1 else [outer_rings[0]]

        if geom_type and coords:
            tags = elem.get("tags", {})
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "id": elem["id"],
                        "name": tags.get("name", ""),
                        "forest_type": tags.get("leaf_type", tags.get("landuse", "unknown")),
                        "ndvi_mean": None,
                        "source": "OpenStreetMap",
                    },
                    "geometry": {"type": geom_type, "coordinates": coords},
                }
            )

    return {
        "type": "FeatureCollection",
        "name": "india_forest_cover",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }


def download(bbox: tuple) -> bool:
    query = build_query(bbox)
    print(f"Query bbox: W={bbox[0]}, S={bbox[1]}, E={bbox[2]}, N={bbox[3]}")

    for url in ENDPOINTS:
        print(f"Trying {url.split('/')[2]}...", end=" ", flush=True)
        try:
            r = requests.post(url, data={"data": query}, timeout=360)
            if r.status_code == 200:
                print("OK — parsing...")
                raw = r.json()
                n_elems = len(raw.get("elements", []))
                print(f"  {n_elems} OSM elements received")

                geojson = overpass_to_geojson(raw)
                n_features = len(geojson["features"])
                print(f"  {n_features} valid polygon features")

                # Atomic write: write to tmp then rename
                tmp = OUT.with_suffix(".tmp")
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(geojson, f)
                tmp.replace(OUT)

                size_kb = OUT.stat().st_size / 1024
                print(f"✅ Saved {size_kb:.0f} KB → {OUT.name}  ({n_features} forest polygons)")
                return True
            else:
                print(f"HTTP {r.status_code}")
        except Exception as e:
            print(f"error: {e}")
        time.sleep(5)

    return False


def main():
    parser = argparse.ArgumentParser(description="Download India forest cover from OSM")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--state",
        choices=list(STATE_BBOXES.keys()),
        default="karnataka",
        help="Pre-defined state bbox (default: karnataka)",
    )
    group.add_argument(
        "--bbox",
        metavar="W,S,E,N",
        help="Custom bbox lon_min,lat_min,lon_max,lat_max",
    )
    args = parser.parse_args()

    if args.bbox:
        try:
            bbox = tuple(float(x) for x in args.bbox.split(","))
            assert len(bbox) == 4
        except Exception:
            print("--bbox must be four comma-separated floats: W,S,E,N")
            sys.exit(1)
    else:
        bbox = STATE_BBOXES[args.state]

    print(f"Downloading India forest cover (OSM) → {OUT}")
    ok = download(bbox)
    if not ok:
        print("❌ All endpoints failed — keeping existing file")
        sys.exit(1)


if __name__ == "__main__":
    main()
