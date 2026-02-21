"""
generate_mock_data.py — Creates realistic mock India forest data for testing.

Run this once before testing:
    python tools/generate_mock_data.py

Creates:
    data/reference/india_forest_cover.geojson     — reference forest polygons
    data/reference/india_protected_areas.geojson  — protected areas
    data/sample_claims/valid_claim.kmz            — 80%+ overlap with forest
    data/sample_claims/partial_claim.kmz          — ~40% overlap
    data/sample_claims/invalid_claim.kmz          — <5% overlap (likely fraud)
    data/sample_claims/protected_overlap.kmz      — overlaps a protected area
"""

import json
import os
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon, mapping


# ─── Real approximate locations in India (lat/lon) ───────────────────────────
# Using actual forest-dense regions for realism

MOCK_FOREST_REGIONS = [
    # (name, forest_type, center_lat, center_lon, approx_size_deg)
    ("Western Ghats - Kodagu Forests", "dense", 12.35, 75.75, 0.4),
    ("Sundarbans Buffer", "mangrove", 21.95, 89.05, 0.3),
    ("Simlipal Biosphere Reserve", "dense", 21.80, 86.50, 0.5),
    ("Nagarhole National Park Area", "dense", 11.90, 76.10, 0.35),
    ("Panna Tiger Reserve Periphery", "dry", 24.75, 80.00, 0.4),
    ("Dampa Tiger Reserve - Mizoram", "dense", 23.45, 92.65, 0.3),
    ("Kalakad Mundanthurai Buffer", "dense", 8.65, 77.35, 0.25),
    ("Bandipur Adjacent Forests", "dense", 11.70, 76.60, 0.3),
    ("Periyar Buffer Zone", "dense", 9.45, 77.10, 0.2),
    ("Corbett Periphery - Uttarakhand", "temperate", 29.55, 79.00, 0.45),
    ("Bhadra Wildlife Sanctuary Area", "dense", 13.70, 75.60, 0.3),
    ("Rajaji National Park Buffer", "dry", 29.85, 78.15, 0.35),
    ("Saranda Forest - Jharkhand", "sal", 22.10, 85.60, 0.4),
    ("Bastar Dense Forest", "dense", 19.10, 81.90, 0.5),
    ("Indravati Buffer Zone", "dense", 18.80, 80.40, 0.35),
]

MOCK_PROTECTED_AREAS = [
    ("Jim Corbett National Park", "national_park", 29.53, 78.78, 0.30),
    ("Sundarbans National Park", "national_park", 21.95, 88.88, 0.40),
    ("Nagarhole National Park", "national_park", 11.99, 76.18, 0.28),
    ("Simlipal National Park", "national_park", 21.84, 86.65, 0.32),
    ("Bandipur National Park", "national_park", 11.67, 76.62, 0.25),
    ("Periyar Tiger Reserve", "tiger_reserve", 9.46, 77.20, 0.22),
    ("Indravati Tiger Reserve", "tiger_reserve", 18.82, 80.55, 0.27),
]


def make_polygon(
    center_lat: float, center_lon: float, size: float, jitter: bool = True
) -> Polygon:
    """Create a roughly rectangular polygon around a center point."""
    if jitter:
        # Add slight randomness to make it look realistic
        size_lat = size * (0.7 + np.random.random() * 0.6)
        size_lon = size * (0.7 + np.random.random() * 0.6)
        offset_lat = (np.random.random() - 0.5) * size * 0.3
        offset_lon = (np.random.random() - 0.5) * size * 0.3
        center_lat += offset_lat
        center_lon += offset_lon
    else:
        size_lat = size
        size_lon = size

    # Create irregular polygon (not a perfect rectangle)
    angles = np.linspace(0, 2 * np.pi, 8, endpoint=False)
    radii_lat = size_lat / 2 * (0.8 + np.random.random(8) * 0.4)
    radii_lon = size_lon / 2 * (0.8 + np.random.random(8) * 0.4)

    coords = [
        (center_lon + np.cos(a) * rl, center_lat + np.sin(a) * rl)
        for a, rl, rb in zip(angles, radii_lon, radii_lat)
    ]
    return Polygon(coords)


def make_reference_geojson():
    """Create mock India forest cover reference GeoJSON."""
    features = []
    np.random.seed(42)  # Reproducible

    for name, forest_type, lat, lon, size in MOCK_FOREST_REGIONS:
        poly = make_polygon(lat, lon, size, jitter=False)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "name": name,
                    "forest_type": forest_type,
                    "ndvi_mean": round(0.55 + np.random.random() * 0.25, 3),
                    "canopy_cover_pct": round(55 + np.random.random() * 30, 1),
                    "source": "FSI_MOCK_2023",
                    "verified_year": 2023,
                },
                "geometry": mapping(poly),
            }
        )

    return {"type": "FeatureCollection", "features": features}


def make_protected_areas_geojson():
    """Create mock protected areas GeoJSON."""
    features = []
    np.random.seed(99)

    for name, pa_type, lat, lon, size in MOCK_PROTECTED_AREAS:
        poly = make_polygon(lat, lon, size, jitter=False)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "name": name,
                    "type": pa_type,
                    "state": "India",
                    "wdpa_id": f"MOCK_{np.random.randint(10000, 99999)}",
                },
                "geometry": mapping(poly),
            }
        )

    return {"type": "FeatureCollection", "features": features}


def polygon_to_kml(polygon: Polygon, name: str, description: str = "") -> str:
    """Convert a Shapely polygon to KML string."""
    coords = polygon.exterior.coords
    coord_str = " ".join(f"{lon},{lat},0" for lon, lat in coords)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{name}</name>
    <Placemark>
      <name>{name}</name>
      <description>{description}</description>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>{coord_str}</coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""


def save_kmz(kml_content: str, output_path: str):
    """Save KML content as a KMZ (zipped KML)."""
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as kmz:
        kmz.writestr("doc.kml", kml_content)


def make_sample_claims(forest_regions: list):
    """
    Create 4 test KMZ files representing different claim scenarios.
    """
    np.random.seed(77)
    claims = []

    # ── 1. VALID CLAIM: polygon mostly inside a real forest region ──
    lat, lon, size = 12.35, 75.75, 0.15  # Inside Western Ghats
    valid_poly = make_polygon(lat, lon, size * 0.5, jitter=True)
    claims.append(
        (
            "valid_claim",
            valid_poly,
            "GreenFuture Ltd — 500 ha forest conservation in Kodagu, Karnataka. "
            "Dense evergreen forest, carbon sequestration project since 2020.",
        )
    )

    # ── 2. PARTIAL CLAIM: polygon half inside, half outside forest ──
    lat, lon, size = 11.90, 76.30, 0.4  # Partially overlaps Nagarhole
    partial_poly = make_polygon(lat, lon, size * 0.6, jitter=True)
    claims.append(
        (
            "partial_claim",
            partial_poly,
            "EcoBalance Corp — 1200 ha reforestation project in Karnataka-Kerala border. "
            "Mixed land use area, claims full forest coverage.",
        )
    )

    # ── 3. INVALID CLAIM: polygon in a non-forested area ──
    # Place in Thar Desert / agricultural flatlands
    invalid_poly = make_polygon(27.5, 73.5, 0.3, jitter=True)
    claims.append(
        (
            "invalid_claim",
            invalid_poly,
            "CarbonMax Inc — 2000 ha dense forest conservation in Rajasthan. "
            "Claims pristine forest coverage with NDVI > 0.6.",
        )
    )

    # ── 4. PROTECTED AREA OVERLAP: polygon overlaps Jim Corbett ──
    lat, lon, size = 29.53, 78.78, 0.2  # Inside Corbett
    protected_poly = make_polygon(lat, lon, size * 0.8, jitter=False)
    claims.append(
        (
            "protected_overlap_claim",
            protected_poly,
            "TerraVerde — 800 ha forest project in Uttarakhand. "
            "Claims forest that is actually within Jim Corbett National Park boundary.",
        )
    )

    return claims


def main():
    output_dirs = [
        "data/reference",
        "data/sample_claims",
    ]
    for d in output_dirs:
        Path(d).mkdir(parents=True, exist_ok=True)

    print("🌲 Generating mock India forest reference data...")
    forest_geojson = make_reference_geojson()
    with open("data/reference/india_forest_cover.geojson", "w") as f:
        json.dump(forest_geojson, f, indent=2)
    print(
        f"  ✓ data/reference/india_forest_cover.geojson ({len(forest_geojson['features'])} polygons)"
    )

    print("\n🏞  Generating mock protected areas...")
    pa_geojson = make_protected_areas_geojson()
    with open("data/reference/india_protected_areas.geojson", "w") as f:
        json.dump(pa_geojson, f, indent=2)
    print(
        f"  ✓ data/reference/india_protected_areas.geojson ({len(pa_geojson['features'])} areas)"
    )

    print("\n📦 Generating sample claim KMZ files...")
    claims = make_sample_claims(MOCK_FOREST_REGIONS)

    for claim_name, polygon, description in claims:
        kml = polygon_to_kml(polygon, claim_name, description)
        kmz_path = f"data/sample_claims/{claim_name}.kmz"
        save_kmz(kml, kmz_path)
        print(f"  ✓ {kmz_path}")

    print("\n✅ Mock data generation complete!")
    print("\nScenarios:")
    print("  valid_claim.kmz            → Should score HIGH trust (>70)")
    print("  partial_claim.kmz          → Should score MEDIUM trust (30-70)")
    print("  invalid_claim.kmz          → Should score LOW/CRITICAL trust (<30)")
    print("  protected_overlap_claim.kmz → Should be flagged as protected area fraud")
    print("\nNow run: uvicorn api.main:app --reload")


if __name__ == "__main__":
    main()
