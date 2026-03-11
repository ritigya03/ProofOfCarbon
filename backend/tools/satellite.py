"""
tools/satellite.py — Fetch NDVI time-series for a bounding box.

Primary: NASA MODIS Terra (MOD13Q1) via Google Earth Engine Python API.
Fallback: Deterministic mock seeded from the centroid lat/lon so results
           are reproducible per location without any API credentials.

NDVI thresholds and time-window settings are loaded from:
  data/config/satellite_thresholds.json
"""

import json
import logging
import math
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MODIS_COLLECTION = "MODIS/061/MOD13Q1"  # 16-day NDVI composites, 250 m (v061 — current)

# ── Load thresholds from JSON config ──────────────────────────────────────────

_THIS_DIR       = Path(__file__).parent.parent   # backend/
_THRESHOLDS_JSON = Path(os.getenv(
    "SATELLITE_THRESHOLDS_JSON",
    str(_THIS_DIR / "data" / "config" / "satellite_thresholds.json")
))


def _load_thresholds() -> dict:
    if not _THRESHOLDS_JSON.exists():
        raise FileNotFoundError(
            f"Satellite thresholds JSON not found at: {_THRESHOLDS_JSON}\n"
            f"  Expected: data/config/satellite_thresholds.json\n"
            f"  Override path with env var SATELLITE_THRESHOLDS_JSON"
        )
    with open(_THRESHOLDS_JSON, encoding="utf-8") as f:
        cfg = json.load(f)
    logger.info(f"[satellite] Loaded thresholds from {_THRESHOLDS_JSON.name}")
    return cfg


# Loaded once at module import
THRESHOLDS = _load_thresholds()

# Convenience aliases (keeps the rest of the code readable)
NDVI_DENSE_FOREST = float(THRESHOLDS["ndvi_dense_forest"])
NDVI_DEGRADED     = float(THRESHOLDS["ndvi_degraded"])
NDVI_BARE         = float(THRESHOLDS["ndvi_bare"])
TREND_DROP_PCT    = float(THRESHOLDS["trend_drop_pct"])
CURRENT_YEARS     = int(THRESHOLDS["current_years"])
HISTORICAL_YEARS  = int(THRESHOLDS["historical_years"])


# ── GEE fetch ────────────────────────────────────────────────────────────────


def _fetch_modis_ndvi(bbox: dict, years: int, offset_years: int = 0) -> Optional[float]:
    """
    Compute mean NDVI over a bbox and time window using Google Earth Engine.

    Args:
        bbox: {"min_lon", "min_lat", "max_lon", "max_lat"}
        years: how many years wide the window is
        offset_years: how many years in the past the window *ends*
                      (0 = ends today, 3 = ends 3 years ago)

    Returns:
        Mean NDVI (float, 0-1) or None on error.
    """
    try:
        import ee
        from datetime import date, timedelta

        end_date   = date.today() - timedelta(days=offset_years * 365)
        start_date = end_date - timedelta(days=years * 365)

        aoi = ee.Geometry.Rectangle(
            [bbox["min_lon"], bbox["min_lat"], bbox["max_lon"], bbox["max_lat"]]
        )

        collection = (
            ee.ImageCollection(MODIS_COLLECTION)
            .filterDate(start_date.isoformat(), end_date.isoformat())
            .filterBounds(aoi)
            .select("NDVI")
        )

        mean_image = collection.mean()
        stats = mean_image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=250,
            maxPixels=1e8,
        )
        ndvi_raw = stats.getInfo().get("NDVI")

        if ndvi_raw is None:
            return None
        # MODIS NDVI is scaled × 10000
        return round(ndvi_raw / 10000, 4)

    except Exception as exc:
        logger.warning(f"[satellite] GEE NDVI fetch failed: {exc}")
        return None


def _pixel_count_estimate(bbox: dict) -> int:
    """Estimate ~250 m pixel count for the bbox (rough)."""
    lat_deg = abs(bbox["max_lat"] - bbox["min_lat"])
    lon_deg = abs(bbox["max_lon"] - bbox["min_lon"])
    lat_km  = lat_deg * 111.0
    lon_km  = lon_deg * 111.0 * math.cos(math.radians((bbox["min_lat"] + bbox["max_lat"]) / 2))
    area_km2 = lat_km * lon_km
    return max(1, int(area_km2 / 0.0625))   # 250 m × 250 m = 0.0625 km²


# ── Mock fallback ─────────────────────────────────────────────────────────────


def _mock_ndvi(bbox: dict) -> dict:
    """
    Generate deterministic, realistic NDVI values seeded by centroid.

    Useful in dev/test mode when GEE credentials are not available.
    The gradient follows a rough India-wide forest distribution:
      - Western Ghats / NE India → high NDVI
      - Rajasthan / Deccan Plateau → low NDVI
    """
    lat  = (bbox["min_lat"] + bbox["max_lat"]) / 2
    lon  = (bbox["min_lon"] + bbox["max_lon"]) / 2

    # Provide high NDVI for known forest/agroforestry regions in our mock data
    # (e.g. Kodagu/Western Ghats area around 12.3N, 75.7E)
    # Meghalaya/Khasi Hills around 25.4N, 91.8E
    is_forest_region = (11.0 <= lat <= 14.5 and 74.5 <= lon <= 77.5) or (20.0 <= lat <= 28.0 and 88.0 <= lon <= 94.0)
    
    seed = math.sin(lat * 7.3 + lon * 3.1) * 0.5 + 0.5   # 0-1
    
    if is_forest_region:
        # High NDVI (0.6 - 0.85) for forest zones
        ndvi_current = round(0.65 + seed * 0.2, 3)
        ndvi_historical = round(ndvi_current - 0.01, 3)
    else:
        # Random distribution (0.25 - 0.78) for other regions
        ndvi_current    = round(0.25 + seed * 0.53, 3)
        ndvi_historical = round(ndvi_current - 0.02 + (math.cos(lat) * 0.01), 3)

    ndvi_historical = max(0.05, min(0.95, ndvi_historical))
    change_pct = ((ndvi_current - ndvi_historical) / max(ndvi_historical, 0.01)) * 100

    if change_pct <= -TREND_DROP_PCT:
        trend = "DECREASING"
    elif change_pct >= TREND_DROP_PCT:
        trend = "INCREASING"
    else:
        trend = "STABLE"

    flags = _build_flags(ndvi_current, trend, change_pct)

    return {
        "ndvi_current_mean":    ndvi_current,
        "ndvi_historical_mean": ndvi_historical,
        "ndvi_trend":           trend,
        "ndvi_anomaly_score":   round(change_pct, 2),
        "pixel_count":          _pixel_count_estimate(bbox),
        "data_source":          "MOCK",
        "flags":                flags,
    }


# ── Flag builder ──────────────────────────────────────────────────────────────


def _build_flags(ndvi_current: float, trend: str, change_pct: float) -> list[str]:
    flags = []

    if ndvi_current >= NDVI_DENSE_FOREST:
        flags.append(f"NDVI {ndvi_current:.2f} — consistent with dense forest / vegetation")
    elif ndvi_current >= NDVI_DEGRADED:
        flags.append(f"NDVI {ndvi_current:.2f} — moderate vegetation; partial or degraded forest")
    elif ndvi_current >= NDVI_BARE:
        flags.append(
            f"WARNING: NDVI {ndvi_current:.2f} — sparse vegetation, unlikely to support carbon claims"
        )
    else:
        flags.append(
            f"CRITICAL: NDVI {ndvi_current:.2f} — near-bare ground; forest claims implausible"
        )

    if trend == "DECREASING":
        flags.append(
            f"CRITICAL: Vegetation has declined {abs(change_pct):.1f}% over the historical baseline — "
            "possible deforestation or land-use change"
        )
    elif trend == "INCREASING":
        flags.append(
            f"Positive trend: Vegetation increased {change_pct:.1f}% — supports reforestation claims"
        )

    return flags


# ── Public API ────────────────────────────────────────────────────────────────


def fetch_ndvi_for_bbox(bbox: dict) -> dict:
    """
    Main entry point. Returns an NDVI analysis dict for the given bbox.

    Tries GEE (real satellite data) first; falls back to deterministic mock
    if GEE credentials are unavailable or the request fails.
    """
    gee_key = os.getenv("GEE_SERVICE_ACCOUNT_KEY")
    service_account = os.getenv("GEE_SERVICE_ACCOUNT_EMAIL")

    if gee_key and service_account:
        logger.info(f"[satellite] GEE credentials found for {service_account}. Attempting real MODIS fetch...")
        try:
            import ee

            # Resolve key path
            key_path = Path(gee_key)
            if not key_path.is_absolute():
                # If backend/tools/satellite.py, .parent.parent is backend/
                key_path = Path(__file__).parent.parent / gee_key
            
            logger.info(f"[satellite] Resolved GEE key path: {key_path}")

            if key_path.exists():
                logger.info(f"[satellite] GEE key file exists. Initializing with ServiceAccountCredentials...")
                credentials = ee.ServiceAccountCredentials(service_account, str(key_path))
                ee.Initialize(credentials)
                logger.info("[satellite] GEE Initialization SUCCESS")
            else:
                logger.warning(f"[satellite] GEE key file NOT FOUND at {key_path}. Trying raw string fallback...")
                credentials = ee.ServiceAccountCredentials(service_account, gee_key)
                ee.Initialize(credentials)
                logger.info("[satellite] GEE Initialization SUCCESS (raw string)")

            ndvi_current    = _fetch_modis_ndvi(bbox, years=CURRENT_YEARS,    offset_years=0)
            ndvi_historical = _fetch_modis_ndvi(bbox, years=HISTORICAL_YEARS, offset_years=CURRENT_YEARS)

            if ndvi_current is not None and ndvi_historical is not None:
                change_pct = ((ndvi_current - ndvi_historical) / max(ndvi_historical, 0.01)) * 100

                if change_pct <= -TREND_DROP_PCT:
                    trend = "DECREASING"
                elif change_pct >= TREND_DROP_PCT:
                    trend = "INCREASING"
                else:
                    trend = "STABLE"

                flags = _build_flags(ndvi_current, trend, change_pct)

                logger.info(
                    f"[satellite] GEE fetch SUCCESS — source: {MODIS_COLLECTION}, "
                    f"current={ndvi_current}, trend={trend}"
                )
                return {
                    "ndvi_current_mean":    ndvi_current,
                    "ndvi_historical_mean": ndvi_historical,
                    "ndvi_trend":           trend,
                    "ndvi_anomaly_score":   round(change_pct, 2),
                    "pixel_count":          _pixel_count_estimate(bbox),
                    "data_source":          MODIS_COLLECTION,
                    "flags":                flags,
                }
            else:
                logger.warning("[satellite] GEE returned empty NDVI data for this bbox/time-window")

        except Exception as exc:
            logger.warning(f"[satellite] GEE pipeline error: {exc}")

    # Fallback to mock if GEE is not configured or failed
    reason = "no GEE credentials" if not gee_key else "fetch failed or empty"
    logger.info(f"[satellite] Using deterministic mock NDVI ({reason})")
    return _mock_ndvi(bbox)
