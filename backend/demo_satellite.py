"""
demo_satellite.py -- See real NASA MODIS satellite NDVI data for Indian forest locations.

Run from the backend directory:
    python demo_satellite.py
"""

import os
import math
from dotenv import load_dotenv

load_dotenv()

# ── Helpers ───────────────────────────────────────────────────────────────────

def ndvi_bar(ndvi: float, width: int = 30) -> str:
    filled = int(ndvi * width)
    return "[" + "#" * filled + "-" * (width - filled) + "]"

def vegetation_label(ndvi: float) -> str:
    if ndvi >= 0.60: return "Dense Forest          *** HIGH ***"
    if ndvi >= 0.40: return "Moderate Forest / Mixed"
    if ndvi >= 0.20: return "Sparse Vegetation      * LOW *"
    if ndvi >= 0.10: return "Degraded Land         ** CONCERN **"
    return "Near Bare Ground      *** RED FLAG ***"

def trend_label(trend: str) -> str:
    return {"INCREASING": "/\\ INCREASING", "DECREASING": "\\/ DECREASING", "STABLE": "== STABLE"}.get(trend, trend)

# ── Test locations ────────────────────────────────────────────────────────────

LOCATIONS = [
    {
        "name":  "Kodagu, Karnataka  (Dense Western Ghats forest)",
        "bbox":  {"min_lon": 75.7, "min_lat": 12.3, "max_lon": 75.9, "max_lat": 12.5},
        "claim": "Evergreen forest, 700 ha -- expect HIGH NDVI",
    },
    {
        "name":  "Jim Corbett, Uttarakhand  (Protected Tiger Reserve)",
        "bbox":  {"min_lon": 78.8, "min_lat": 29.4, "max_lon": 79.0, "max_lat": 29.6},
        "claim": "Sal & mixed forest -- expect HIGH NDVI",
    },
    {
        "name":  "Thar Desert, Rajasthan  (Arid / FRAUD TEST)",
        "bbox":  {"min_lon": 72.0, "min_lat": 26.5, "max_lon": 72.2, "max_lat": 26.7},
        "claim": "Company claims forest/plantation -- expect VERY LOW NDVI",
    },
    {
        "name":  "Sundarbans, West Bengal  (Mangrove forest)",
        "bbox":  {"min_lon": 88.8, "min_lat": 21.8, "max_lon": 89.0, "max_lat": 22.0},
        "claim": "Mangrove carbon project -- expect MODERATE/HIGH NDVI",
    },
    {
        "name":  "Deccan Plateau, Maharashtra  (Mixed land use)",
        "bbox":  {"min_lon": 75.5, "min_lat": 17.5, "max_lon": 75.7, "max_lat": 17.7},
        "claim": "Agroforestry project -- expect MODERATE NDVI",
    },
]

# ── GEE fetch ─────────────────────────────────────────────────────────────────

def fetch_ndvi_gee(bbox: dict, years: int, offset_years: int = 0):
    import ee
    from datetime import date, timedelta
    end   = date.today() - timedelta(days=offset_years * 365)
    start = end - timedelta(days=years * 365)
    aoi = ee.Geometry.Rectangle(
        [bbox["min_lon"], bbox["min_lat"], bbox["max_lon"], bbox["max_lat"]]
    )
    col = (
        ee.ImageCollection("MODIS/061/MOD13Q1")
        .filterDate(start.isoformat(), end.isoformat())
        .filterBounds(aoi)
        .select("NDVI")
    )
    stats = col.mean().reduceRegion(ee.Reducer.mean(), aoi, 250, maxPixels=1e8).getInfo()
    raw = stats.get("NDVI")
    return round(raw / 10000, 4) if raw else None

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    SEP = "=" * 65
    print("\n" + SEP)
    print("  ProofOfCarbon -- Live NASA MODIS Satellite NDVI Viewer")
    print("  Source : MODIS/061/MOD13Q1 | 250m resolution | 16-day avg")
    print("  Period : last 3 years (current)  vs  3-6 years ago (history)")
    print(SEP)

    email = os.getenv("GEE_SERVICE_ACCOUNT_EMAIL")
    key   = os.getenv("GEE_SERVICE_ACCOUNT_KEY")

    use_gee = False
    if email and key and os.path.exists(key):
        try:
            import ee
            creds = ee.ServiceAccountCredentials(email, key)
            ee.Initialize(creds)
            print(f"\n[OK] GEE connected as: {email}")
            use_gee = True
        except Exception as e:
            print(f"\n[WARN] GEE auth failed ({e}), using deterministic mock data.")
    else:
        print("\n[WARN] GEE credentials not found -- using deterministic mock data.")
        print("       Set GEE_SERVICE_ACCOUNT_EMAIL + GEE_SERVICE_ACCOUNT_KEY in .env\n")

    for i, loc in enumerate(LOCATIONS, 1):
        print(f"\n{'─' * 65}")
        print(f"  Location {i}: {loc['name']}")
        print(f"  Claim   : {loc['claim']}")
        print(f"  BBox    : lon [{loc['bbox']['min_lon']}, {loc['bbox']['max_lon']}]"
              f"  lat [{loc['bbox']['min_lat']}, {loc['bbox']['max_lat']}]")
        print()

        if use_gee:
            print("  Fetching from NASA GEE... ", end="", flush=True)
            try:
                ndvi_now  = fetch_ndvi_gee(loc["bbox"], years=3, offset_years=0)
                ndvi_hist = fetch_ndvi_gee(loc["bbox"], years=3, offset_years=3)
                print("done.")
            except Exception as e:
                print(f"ERROR: {e}")
                continue
        else:
            lat  = (loc["bbox"]["min_lat"] + loc["bbox"]["max_lat"]) / 2
            lon  = (loc["bbox"]["min_lon"] + loc["bbox"]["max_lon"]) / 2
            seed = math.sin(lat * 7.3 + lon * 3.1) * 0.5 + 0.5
            ndvi_now  = round(0.25 + seed * 0.53, 3)
            ndvi_hist = round(ndvi_now - 0.02, 3)

        if ndvi_now is None or ndvi_hist is None:
            print("  [ERROR] No MODIS data for this area/period.")
            continue

        change_pct = ((ndvi_now - ndvi_hist) / max(ndvi_hist, 0.01)) * 100
        if   change_pct <= -10: trend = "DECREASING"
        elif change_pct >=  10: trend = "INCREASING"
        else:                    trend = "STABLE"

        # Verdict
        print(f"  Current  NDVI (last 3 yr) : {ndvi_now:.4f}  {ndvi_bar(ndvi_now)}")
        print(f"  Historic NDVI (3-6 yr ago): {ndvi_hist:.4f}  {ndvi_bar(ndvi_hist)}")
        print(f"  Trend                     : {trend_label(trend)}  ({change_pct:+.1f}% change)")
        print(f"  Vegetation class          : {vegetation_label(ndvi_now)}")

        if ndvi_now < 0.20:
            print(f"\n  !! RED FLAG: NDVI {ndvi_now:.2f} far too low to support any forest claim")
        elif ndvi_now < 0.40:
            print(f"\n  !  WARNING : NDVI {ndvi_now:.2f} -- sparse vegetation, verify carefully")
        else:
            print(f"\n  OK: NDVI {ndvi_now:.2f} is consistent with forest/vegetation claim")

        if trend == "DECREASING":
            print(f"  !! DEFORESTATION SIGNAL: declined {abs(change_pct):.1f}% vs historical baseline")

    print("\n" + SEP)
    print("  These NDVI values feed into SatelliteEvidenceAgent at /analyze")
    print("  and adjust the final trust score automatically.")
    print(SEP + "\n")


if __name__ == "__main__":
    main()
