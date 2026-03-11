"""
kmz_parser.py — Parse KMZ/KML files into GeoDataFrames.

KMZ is just a zipped KML. KML contains geographic features (polygons, points)
with metadata. We extract, reproject, and return a clean GeoDataFrame.
"""

import zipfile
import tempfile
import logging
from pathlib import Path

import fiona
import geopandas as gpd
from pyproj import Transformer
import numpy as np

fiona.drvsupport.supported_drivers["KML"] = "rw"
fiona.drvsupport.supported_drivers["LIBKML"] = "rw"

logger = logging.getLogger(__name__)


def parse_kmz(kmz_path: str) -> gpd.GeoDataFrame:
    """
    Parse a KMZ file and return a GeoDataFrame in WGS84 (EPSG:4326).

    Args:
        kmz_path: Path to the .kmz file

    Returns:
        GeoDataFrame with geometry column + any KML attributes
    """
    # Ensure drivers are registered in the current thread/process
    try:
        fiona.drvsupport.supported_drivers["KML"] = "rw"
        fiona.drvsupport.supported_drivers["LIBKML"] = "rw"
    except Exception as e:
        logger.warning(f"Failed to register KML drivers: {e}")

    with zipfile.ZipFile(kmz_path, "r") as kmz:
        with tempfile.TemporaryDirectory() as tmpdir:
            kmz.extractall(tmpdir)
            kml_files = list(Path(tmpdir).glob("**/*.kml"))

            if not kml_files:
                raise ValueError(f"No KML file found inside {kmz_path}")

            kml_path = str(kml_files[0])
            logger.info(f"Parsing KML: {kml_path}")

            # Try reading all layers
            try:
                layers = fiona.listlayers(kml_path)
                logger.info(f"Fiona layers: {layers}")
            except Exception as e:
                logger.error(f"Fiona failed to list layers: {e}")
                layers = [None] # Try reading default layer
                
            gdfs = []
            for layer in layers:
                # Try multiple drivers: KML, LIBKML, or None
                success = False
                for driver in ["KML", "LIBKML", None]:
                    try:
                        logger.info(f"Attempting read with driver={driver}, layer={layer}, engine=fiona")
                        # Force engine="fiona" because pyogrio is unreliable with KML on some systems
                        gdf = gpd.read_file(kml_path, driver=driver, layer=layer, engine="fiona")
                        if not gdf.empty and gdf.geometry.notna().any():
                            gdfs.append(gdf)
                            logger.info(f"Successfully read layer '{layer}' with driver {driver}")
                            success = True
                            break
                    except Exception as e:
                        logger.debug(f"Driver {driver} failed for layer '{layer}': {e}")
                
                if not success:
                    logger.warning(f"All drivers failed for layer '{layer}'")

            if not gdfs:
                # One last attempt without specific layer
                try:
                    logger.info("One last attempt reading without layer/driver (fiona engine)...")
                    gdf = gpd.read_file(kml_path, engine="fiona")
                    if not gdf.empty:
                        gdfs.append(gdf)
                except Exception as e:
                    logger.error(f"Final fallback failed: {e}")

            if not gdfs:
                raise ValueError("No valid geometries found in KML after trying multiple drivers")

            combined = gpd.GeoDataFrame(
                gpd.pd.concat(gdfs, ignore_index=True),
                crs="EPSG:4326"
            )

    combined = combined[combined.geometry.notna()].copy()
    combined = combined.set_crs("EPSG:4326", allow_override=True)
    logger.info(f"Parsed {len(combined)} features from KMZ")
    return combined


def get_utm_zone_crs(gdf: gpd.GeoDataFrame) -> str:
    """
    Determine the best UTM zone for a GeoDataFrame based on its centroid longitude.
    Critical for accurate area calculation across India's wide longitude range.

    India spans roughly 68°E to 97°E:
    - Zone 43N (EPSG:32643): 72–78°E  → Gujarat, MP, Maharashtra
    - Zone 44N (EPSG:32644): 78–84°E  → UP, Odisha, AP, Karnataka
    - Zone 45N (EPSG:32645): 84–90°E  → West Bengal, Bihar
    - Zone 46N (EPSG:32646): 90–96°E  → Northeast India
    """
    centroid = gdf.to_crs("EPSG:4326").geometry.unary_union.centroid
    lon = centroid.x

    if lon < 72:
        return "EPSG:32642"  # Zone 42N — Rajasthan/Gujarat west
    elif lon < 78:
        return "EPSG:32643"
    elif lon < 84:
        return "EPSG:32644"
    elif lon < 90:
        return "EPSG:32645"
    else:
        return "EPSG:32646"


def get_area_hectares(gdf: gpd.GeoDataFrame) -> float:
    """
    Returns total area in hectares using the correct UTM zone for India.
    Never use EPSG:4326 for area — degrees != meters.
    """
    utm_crs = get_utm_zone_crs(gdf)
    projected = gdf.to_crs(utm_crs)
    area_m2 = projected.geometry.area.sum()
    area_ha = area_m2 / 10_000
    logger.info(f"Calculated area: {area_ha:.2f} ha using {utm_crs}")
    return round(float(area_ha), 2)


def get_bounding_box(gdf: gpd.GeoDataFrame) -> dict:
    """Returns bounding box in WGS84 for satellite API queries."""
    gdf_4326 = gdf.to_crs("EPSG:4326")
    bounds = gdf_4326.geometry.total_bounds  # [minx, miny, maxx, maxy]
    return {
        "min_lon": round(float(bounds[0]), 6),
        "min_lat": round(float(bounds[1]), 6),
        "max_lon": round(float(bounds[2]), 6),
        "max_lat": round(float(bounds[3]), 6),
    }