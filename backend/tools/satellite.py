"""
tools/satellite.py — Fetch NDVI time-series for a bounding box.

Primary: NASA MODIS Terra (MOD13Q1) via Google Earth Engine Python API.
Fallback: Deterministic mock seeded from the centroid lat/lon so results
           are reproducible per location without any API credentials.
"""

import logging
import math
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

MODIS_COLLECTION = "MODIS/061/MOD13Q1"   # 16-day NDVI composites, 250 m (v061 — current)
CURRENT_YEARS = 3      # how many years = "current" period
HISTORICAL_YEARS = 3   # how many years before that = "historical" baseline

# Thresholds for flagging
NDVI_DENSE_FOREST = 0.50
NDVI_DEGRADED     = 0.30
NDVI_BARE         = 0.10
TREND_DROP_PCT    = 10.0   # ≥10 % decline → DECREASING flag


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

    # Seed a simple deterministic value from lat/lon
    seed = math.sin(lat * 7.3 + lon * 3.1) * 0.5 + 0.5   # 0-1

    # Map seed into realistic NDVI band for India's forests (0.25 – 0.78)
    ndvi_current    = round(0.25 + seed * 0.53, 3)
    # Historical slightly lower to simulate very slight recovery trend
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
    Main entry point.  Returns an NDVI analysis dict for the given bbox.

    Tries GEE (real satellite data) first; falls back to deterministic mock
    if GEE credentials are unavailable or the request fails.

    Args:
        bbox: {"min_lon", "min_lat", "max_lon", "max_lat"}

    Returns:
        {
            "ndvi_current_mean":    float,   # mean NDVI, last 3 years
            "ndvi_historical_mean": float,   # mean NDVI, 3-6 years ago
            "ndvi_trend":           str,     # INCREASING | STABLE | DECREASING
            "ndvi_anomaly_score":   float,   # % change vs historical
            "pixel_count":          int,     # ~250 m pixels sampled
            "data_source":          str,     # MODIS_MOD13Q1 | MOCK
            "flags":                list[str]
        }
    """
    gee_key = os.getenv("GEE_SERVICE_ACCOUNT_KEY")

    if gee_key:
        logger.info("[satellite] GEE credentials found — attempting real MODIS fetch")
        try:
            import ee
            import json

            service_account = os.getenv("GEE_SERVICE_ACCOUNT_EMAIL", "")
            credentials = ee.ServiceAccountCredentials(service_account, gee_key)
            ee.Initialize(credentials)

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
                    f"[satellite] GEE fetch OK — current={ndvi_current}, "
                    f"historical={ndvi_historical}, trend={trend}"
                )
                return {
                    "ndvi_current_mean":    ndvi_current,
                    "ndvi_historical_mean": ndvi_historical,
                    "ndvi_trend":           trend,
                    "ndvi_anomaly_score":   round(change_pct, 2),
                    "pixel_count":          _pixel_count_estimate(bbox),
                    "data_source":          "MODIS_MOD13Q1",
                    "flags":                flags,
                }

        except Exception as exc:
            logger.warning(f"[satellite] GEE pipeline failed, using mock: {exc}")

    logger.info("[satellite] Using deterministic mock NDVI (no GEE credentials)")
    return _mock_ndvi(bbox)
