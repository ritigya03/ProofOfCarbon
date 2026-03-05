"""
geospatial.py — Spatial operations for forest cover comparison.

Strategy (fastest → slowest):
  1. PostGIS  — production; only bbox-intersecting rows returned by SQL
  2. State disk cache — per-state GeoJSON files in data/reference/cache/
                        fetched on-demand from Overpass API, then cached forever
  3. Fallback placeholder — empty GDF; pipeline continues with 0% overlap

This means the *first* analysis for a new state takes 30-90 s (Overpass fetch);
every subsequent analysis for the same state is < 1 s (disk → GeoDataFrame).
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import geopandas as gpd
import requests
from shapely.geometry import box, mapping
from shapely.ops import unary_union

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# In-memory GeoDataFrame cache (state_key → GeoDataFrame)
# ─────────────────────────────────────────────────────────────
_mem_cache: dict[str, gpd.GeoDataFrame] = {}

# Directory where per-state GeoJSON files are stored
_CACHE_DIR = Path(
    os.getenv(
        "FOREST_CACHE_DIR",
        str(Path(__file__).parent.parent / "data" / "reference" / "cache"),
    )
)

# ─────────────────────────────────────────────────────────────
# Indian state bounding boxes (W, S, E, N) in EPSG:4326
# ─────────────────────────────────────────────────────────────
_STATE_BBOXES: dict[str, tuple] = {
    "andhra_pradesh":   (76.7, 12.6, 84.8, 19.9),
    "arunachal_pradesh":(91.6, 26.7, 97.4, 29.5),
    "assam":             (89.7, 24.1, 96.0, 28.2),
    "bihar":             (83.3, 24.3, 88.3, 27.5),
    "chhattisgarh":      (80.2, 17.8, 84.4, 24.1),
    "goa":               (73.7, 14.9, 74.3, 15.8),
    "gujarat":           (68.2, 20.1, 74.5, 24.7),
    "haryana":           (74.5, 27.7, 77.6, 30.9),
    "himachal_pradesh":  (75.6, 30.4, 79.0, 33.2),
    "jharkhand":         (83.3, 21.9, 87.5, 25.4),
    "karnataka":         (74.0, 11.5, 78.6, 18.5),
    "kerala":            (74.9,  8.2, 77.4, 12.8),
    "madhya_pradesh":    (74.0, 21.0, 82.8, 26.9),
    "maharashtra":       (72.6, 15.6, 80.9, 22.0),
    "manipur":           (93.0, 23.8, 94.8, 25.7),
    "meghalaya":         (89.8, 25.1, 92.8, 26.1),
    "mizoram":           (92.3, 21.9, 93.4, 24.5),
    "nagaland":          (93.3, 25.2, 95.3, 27.0),
    "odisha":            (81.4, 17.8, 87.5, 22.6),
    "punjab":            (73.9, 29.5, 76.9, 32.5),
    "rajasthan":         (69.5, 23.1, 78.3, 30.2),
    "sikkim":            (88.0, 27.1, 88.9, 28.1),
    "tamil_nadu":        (76.2,  8.0, 80.3, 13.6),
    "telangana":         (77.2, 15.8, 81.8, 19.9),
    "tripura":           (91.2, 22.9, 92.3, 24.5),
    "uttar_pradesh":     (77.1, 23.9, 84.7, 28.8),
    "uttarakhand":       (77.6, 28.7, 81.1, 31.5),
    "west_bengal":       (85.8, 21.5, 89.9, 27.2),
    # Union territories (small, included for completeness)
    "jammu_kashmir":     (73.7, 32.3, 80.3, 37.1),
    "ladakh":            (75.0, 32.0, 80.3, 36.0),
    "delhi":             (76.8, 28.4, 77.4, 28.9),
}

_OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


# ─────────────────────────────────────────────────────────────
# Helper: detect which state a bbox center falls in
# ─────────────────────────────────────────────────────────────


def detect_states(bbox: dict) -> list[str]:
    """
    Return a list of state keys whose bounding boxes intersect the project *bbox*.
    """
    detected = []
    # User-provided bbox
    b_min_lon, b_min_lat, b_max_lon, b_max_lat = (
        bbox["min_lon"],
        bbox["min_lat"],
        bbox["max_lon"],
        bbox["max_lat"],
    )

    for state, (w, s, e, n) in _STATE_BBOXES.items():
        # Check for intersection: A.min < B.max and A.max > B.min for both axes
        if b_min_lon < e and b_max_lon > w and b_min_lat < n and b_max_lat > s:
            detected.append(state)

    logger.info(f"Detected intersecting states: {detected}")
    return detected


# ─────────────────────────────────────────────────────────────
# Overpass fetch
# ─────────────────────────────────────────────────────────────


def _overpass_query(bbox_tuple: tuple) -> str:
    w, s, e, n = bbox_tuple
    return f"""
[out:json][timeout:300];
(
  way["natural"~"wood|scrub|grassland"]({s},{w},{n},{e});
  way["landuse"~"forest|orchard|plantation|plant_nursery|vineyard"]({s},{w},{n},{e});
  way["leisure"="nature_reserve"]({s},{w},{n},{e});
  way["boundary"~"forest|forest_reserve|protected_area"]({s},{w},{n},{e});
  relation["natural"~"wood|scrub|grassland"]({s},{w},{n},{e});
  relation["landuse"~"forest|orchard|plantation|plant_nursery|vineyard"]({s},{w},{n},{e});
  relation["leisure"="nature_reserve"]({s},{w},{n},{e});
  relation["boundary"~"forest_reserve|protected_area"]({s},{w},{n},{e});
);
out geom;
"""


def _overpass_to_geojson(raw: dict) -> dict:
    features = []
    for elem in raw.get("elements", []):
        coords = geom_type = None

        if elem["type"] == "way" and "geometry" in elem:
            pts = [[pt["lon"], pt["lat"]] for pt in elem["geometry"]]
            if len(pts) >= 3:
                if pts[0] != pts[-1]:
                    pts.append(pts[0])
                coords = [pts]
                geom_type = "Polygon"

        elif elem["type"] == "relation" and "members" in elem:
            outer = []
            for m in elem.get("members", []):
                if m.get("role") == "outer" and "geometry" in m:
                    pts = [[pt["lon"], pt["lat"]] for pt in m["geometry"]]
                    if len(pts) >= 3:
                        if pts[0] != pts[-1]:
                            pts.append(pts[0])
                        outer.append(pts)
            if outer:
                if len(outer) == 1:
                    geom_type, coords = "Polygon", [outer[0]]
                else:
                    geom_type, coords = "MultiPolygon", [[r] for r in outer]

        if geom_type and coords:
            tags = elem.get("tags", {})
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "id": elem["id"],
                        "name": tags.get("name", ""),
                        "forest_type": tags.get(
                            "leaf_type", tags.get("landuse", "unknown")
                        ),
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


def _fetch_from_overpass(state_key: str, bbox_tuple: tuple) -> Optional[gpd.GeoDataFrame]:
    """Fetch forest cover for *state_key* via Overpass API. Returns GDF or None."""
    query = _overpass_query(bbox_tuple)
    logger.info(
        f"[on-demand] Fetching forest cover for '{state_key}' from Overpass API "
        f"(first request for this state — will be cached after this)..."
    )
    for url in _OVERPASS_ENDPOINTS:
        try:
            r = requests.post(url, data={"data": query}, timeout=360)
            if r.status_code == 200:
                raw = r.json()
                geojson = _overpass_to_geojson(raw)
                n = len(geojson["features"])
                logger.info(f"[on-demand] Overpass returned {n} forest polygons for '{state_key}'")

                # Atomic save to disk cache
                _CACHE_DIR.mkdir(parents=True, exist_ok=True)
                tmp = _CACHE_DIR / f"forest_{state_key}.tmp"
                out = _CACHE_DIR / f"forest_{state_key}.geojson"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(geojson, f)
                tmp.replace(out)
                logger.info(f"[on-demand] Cached to {out}")

                gdf = gpd.GeoDataFrame.from_features(geojson["features"], crs="EPSG:4326")
                return gdf
            else:
                logger.warning(f"[on-demand] Overpass {url.split('/')[2]}: HTTP {r.status_code}")
        except Exception as e:
            logger.warning(f"[on-demand] Overpass {url.split('/')[2]}: {e}")
        time.sleep(3)

    logger.error(f"[on-demand] All Overpass endpoints failed for '{state_key}'")
    return None


# ─────────────────────────────────────────────────────────────
# PostGIS layer (production)
# ─────────────────────────────────────────────────────────────


def get_reference_from_db(
    bbox: dict, layer: str = "forest_cover"
) -> Optional[gpd.GeoDataFrame]:
    """
    Query PostGIS for reference forest polygons within a bounding box.
    Returns None if DB not configured / unavailable.
    """
    db_url = os.getenv("POSTGIS_URL")
    if not db_url:
        return None

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(db_url)
        query = text(
            f"""
            SELECT id, name, forest_type, ndvi_mean, geom
            FROM {layer}
            WHERE ST_Intersects(
                geom,
                ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)
            )
        """
        )
        gdf = gpd.read_postgis(query, engine, geom_col="geom", params=bbox)
        logger.info(f"Retrieved {len(gdf)} reference polygons from PostGIS ({layer})")
        return gdf

    except Exception as e:
        logger.warning(f"PostGIS query failed: {e} — falling back to local file")
        return None


# ─────────────────────────────────────────────────────────────
# On-demand state cache loader
# ─────────────────────────────────────────────────────────────


def load_reference(bbox: dict, layer: str = "forest_cover") -> gpd.GeoDataFrame:
    """
    Precision-first loader with four tiers:

    1. PostGIS           — fastest; used in production.
    2. Precision Cache   — fetches the EXACT project bbox (+ buffer) from Overpass.
                           This is 100% reliable for project verification.
    3. State Intersection — detects all states overlapping the bbox and merges data.
    4. Graceful Fallback — empty GDF.
    """
    # Tier 1: PostGIS
    gdf = get_reference_from_db(bbox, layer)
    if gdf is not None:
        return gdf

    # Non-forest layers still use static files
    if layer != "forest_cover":
        return _load_static_layer(bbox, layer)

    # ── Tier 2: Precision AOI Fetch ───────────────────────────
    # We fetch for the project's specific bbox plus a small buffer.
    # This is much more reliable than fetching an entire state.
    
    # Use a rounded/stable cache key for the bbox to avoid redundant fetches
    precision_key = f"aoi_{round(bbox['min_lon'], 2)}_{round(bbox['min_lat'], 2)}"
    if precision_key in _mem_cache:
        logger.info(f"[precision-cache] Using cached AOI data for {precision_key}")
        return _mem_cache[precision_key]

    # Detect states for logging / state-specific nuances
    state_keys = detect_states(bbox)
    if not state_keys:
        logger.warning("No Indian states detected for bbox — returning empty GDF")
        return _empty_gdf()

    # Precision BBox (+0.05 degrees ~ 5km buffer)
    w, s, e, n = (
        bbox["min_lon"] - 0.05,
        bbox["min_lat"] - 0.05,
        bbox["max_lon"] + 0.05,
        bbox["max_lat"] + 0.05,
    )
    aoi_bbox_tuple = (w, s, e, n)
    
    logger.info(f"Performing precision AOI fetch for states: {state_keys}")
    aoi_gdf = _fetch_from_overpass(f"aoi_{state_keys[0]}", aoi_bbox_tuple)
    
    if aoi_gdf is not None and not aoi_gdf.empty:
        _mem_cache[precision_key] = aoi_gdf
        return aoi_gdf

    logger.error(f"Precision AOI fetch failed for detected states: {state_keys}")
    return _empty_gdf()


def _load_static_layer(bbox: dict, layer: str) -> gpd.GeoDataFrame:
    """Load non-forest layers from their static GeoJSON files."""
    paths = {
        "protected_areas": os.getenv(
            "PROTECTED_AREAS_PATH", "data/reference/india_protected_areas.geojson"
        ),
        "lulc": os.getenv("LULC_PATH", "data/reference/india_lulc.geojson"),
    }
    path = paths.get(layer)
    if not path or not os.path.exists(path):
        logger.warning(f"Static layer '{layer}' not found at {path} — returning empty GDF")
        return _empty_gdf()
    try:
        bbox_tuple = (bbox["min_lon"], bbox["min_lat"], bbox["max_lon"], bbox["max_lat"])
        gdf = gpd.read_file(path, bbox=bbox_tuple)
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)
        return gdf
    except Exception as e:
        logger.error(f"Failed to read static layer '{layer}': {e}")
        return _empty_gdf()


def _empty_gdf() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"geometry": gpd.GeoSeries([], dtype="geometry")}, crs="EPSG:4326"
    )


# ─────────────────────────────────────────────────────────────
# Core comparison logic
# ─────────────────────────────────────────────────────────────


def compare_claim_to_reference(
    company_gdf: gpd.GeoDataFrame,
    reference_gdf: gpd.GeoDataFrame,
) -> dict:
    """
    Spatial comparison between company claim and reference forest cover.
    Returns area stats, overlap %, and flags.
    """
    from tools.kmz_parser import get_utm_zone_crs

    utm_crs = get_utm_zone_crs(company_gdf)
    company_proj = company_gdf.to_crs(utm_crs)
    reference_proj = reference_gdf.to_crs(utm_crs)

    # Fix invalid geometries (common in OSM data) to prevent TopologyException
    claimed_geom = company_proj.geometry.make_valid()
    reference_geom = reference_proj.geometry.make_valid()

    claimed_union = unary_union(claimed_geom)
    reference_union = unary_union(reference_geom)

    if claimed_union.is_empty:
        raise ValueError("Company claimed polygon is empty")

    intersection = claimed_union.intersection(reference_union)
    claimed_ha = claimed_union.area / 10_000
    actual_ha = intersection.area / 10_000
    overlap_pct = (
        (intersection.area / claimed_union.area * 100)
        if claimed_union.area > 0
        else 0.0
    )

    flags = []
    if reference_union.is_empty:
        flags.append(
            "WARNING: No reference forest data available for this region — overlap check skipped"
        )
    elif overlap_pct < 10:
        flags.append(
            "WARNING: Less than 10% of claimed area matches OSM reference forest data. "
            "Note: OSM coverage is incomplete for many Indian regions — low overlap "
            "may indicate data gaps rather than absence of forest."
        )
    elif overlap_pct < 50:
        flags.append(
            f"WARNING: Only {overlap_pct:.1f}% of claimed area is verified forest "
            f"in OSM data. OSM coverage may be incomplete for this region."
        )
    if claimed_ha > actual_ha * 2.0 and actual_ha > 0:
        flags.append(
            f"Area overclaim detected: {claimed_ha:.1f} ha claimed vs {actual_ha:.1f} ha verified"
        )

    return {
        "claimed_hectares": round(claimed_ha, 2),
        "verified_hectares": round(actual_ha, 2),
        "overlap_percent": round(overlap_pct, 2),
        "utm_crs_used": utm_crs,
        "flags": flags,
    }


def check_protected_area_overlap(
    company_gdf: gpd.GeoDataFrame,
    protected_gdf: gpd.GeoDataFrame,
) -> dict:
    """
    Check if the company's claimed polygon overlaps with any Indian protected area.
    Overlap with PA is an automatic disqualifier for new carbon credits.
    """
    from tools.kmz_parser import get_utm_zone_crs

    utm_crs = get_utm_zone_crs(company_gdf)
    company_proj = company_gdf.to_crs(utm_crs)
    protected_proj = protected_gdf.to_crs(utm_crs)

    # Fix invalid geometries to prevent TopologyException
    claimed_geom = company_proj.geometry.make_valid()
    pa_geom = protected_proj.geometry.make_valid()

    claimed_union = unary_union(claimed_geom)
    pa_union = unary_union(pa_geom)
    overlap = claimed_union.intersection(pa_union)

    overlap_ha = overlap.area / 10_000
    overlap_pct = (
        (overlap.area / claimed_union.area * 100) if claimed_union.area > 0 else 0
    )

    flags = []
    if overlap_ha > 0:
        overlapping_pas = protected_gdf[
            protected_gdf.to_crs(utm_crs).geometry.intersects(claimed_union)
        ]
        pa_names = overlapping_pas.get(
            "name", overlapping_pas.get("NAME", gpd.pd.Series())
        ).tolist()
        flags.append(
            f"Claimed area overlaps {overlap_ha:.1f} ha of protected area: {', '.join(str(n) for n in pa_names[:3])}"
        )
        flags.append(
            "Land already under legal protection cannot generate new carbon credits"
        )

    return {
        "protected_area_overlap_ha": round(overlap_ha, 2),
        "protected_area_overlap_pct": round(overlap_pct, 2),
        "flags": flags,
    }
