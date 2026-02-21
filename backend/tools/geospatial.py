"""
geospatial.py — Spatial operations for forest cover comparison.

Uses PostGIS (via SQLAlchemy + psycopg2) as the primary reference store.
Falls back to in-memory GeoDataFrame comparison when DB is unavailable (dev/test mode).
"""

import logging
import os
from typing import Optional

import geopandas as gpd
from shapely.ops import unary_union
from shapely.geometry import mapping
import json

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# PostGIS / Vector DB layer
# ─────────────────────────────────────────────


def get_reference_from_db(
    bbox: dict, layer: str = "forest_cover"
) -> Optional[gpd.GeoDataFrame]:
    """
    Query PostGIS for reference forest polygons within a bounding box.
    This is the production path — avoids loading full India dataset into memory.

    Args:
        bbox: {"min_lon", "min_lat", "max_lon", "max_lat"}
        layer: Table name in PostGIS (forest_cover, protected_areas, lulc)

    Returns:
        GeoDataFrame or None if DB not available
    """
    db_url = os.getenv("POSTGIS_URL")
    if not db_url:
        logger.info("POSTGIS_URL not set — falling back to local file")
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


def get_reference_from_file(layer: str = "forest_cover") -> gpd.GeoDataFrame:
    """
    Load reference data from local GeoJSON file.
    Used in dev/test when PostGIS is not running.
    """
    paths = {
        "forest_cover": os.getenv(
            "FOREST_REFERENCE_PATH", "data/reference/india_forest_cover.geojson"
        ),
        "protected_areas": os.getenv(
            "PROTECTED_AREAS_PATH", "data/reference/india_protected_areas.geojson"
        ),
        "lulc": os.getenv("LULC_PATH", "data/reference/india_lulc.geojson"),
    }
    path = paths.get(layer)
    if not path or not os.path.exists(path):
        raise FileNotFoundError(
            f"Reference file not found: {path}. "
            f"Either set POSTGIS_URL or place GeoJSON at {path}"
        )
    gdf = gpd.read_file(path)
    return gdf.set_crs("EPSG:4326", allow_override=True)


def load_reference(bbox: dict, layer: str = "forest_cover") -> gpd.GeoDataFrame:
    """
    Smart loader: tries PostGIS first, falls back to local file.
    In production with PostGIS, only the bbox-intersecting polygons are loaded — huge memory saving.
    """
    gdf = get_reference_from_db(bbox, layer)
    if gdf is None:
        gdf = get_reference_from_file(layer)
        # Clip to bbox for efficiency
        from shapely.geometry import box

        bbox_geom = box(
            bbox["min_lon"], bbox["min_lat"], bbox["max_lon"], bbox["max_lat"]
        )
        gdf = gdf[gdf.geometry.intersects(bbox_geom)].copy()
        logger.info(f"Clipped to {len(gdf)} polygons in bbox")
    return gdf


# ─────────────────────────────────────────────
# Core comparison logic
# ─────────────────────────────────────────────


def compare_claim_to_reference(
    company_gdf: gpd.GeoDataFrame,
    reference_gdf: gpd.GeoDataFrame,
) -> dict:
    """
    Spatial comparison between company claim and reference forest cover.

    Returns a dict with area stats, overlap %, and flags.
    """
    from tools.kmz_parser import get_utm_zone_crs

    utm_crs = get_utm_zone_crs(company_gdf)
    company_proj = company_gdf.to_crs(utm_crs)
    reference_proj = reference_gdf.to_crs(utm_crs)

    claimed_union = unary_union(company_proj.geometry)
    reference_union = unary_union(reference_proj.geometry)

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
    if overlap_pct < 10:
        flags.append(
            "CRITICAL: Less than 10% of claimed area matches verified forest cover"
        )
    elif overlap_pct < 50:
        flags.append(
            f"WARNING: Only {overlap_pct:.1f}% of claimed area is verified forest"
        )
    if claimed_ha > actual_ha * 1.5 and actual_ha > 0:
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

    claimed_union = unary_union(company_proj.geometry)
    pa_union = unary_union(protected_proj.geometry)
    overlap = claimed_union.intersection(pa_union)

    overlap_ha = overlap.area / 10_000
    overlap_pct = (
        (overlap.area / claimed_union.area * 100) if claimed_union.area > 0 else 0
    )

    flags = []
    if overlap_ha > 0:
        # Try to get PA names from the overlapping features
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
