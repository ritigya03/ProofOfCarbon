/**
 * SatelliteMap.tsx — Leaflet map showing the claimed KMZ bbox on real satellite imagery.
 * Uses ESRI World Imagery tiles (free, no API key required).
 *
 * Props:
 *   bbox:             { min_lon, min_lat, max_lon, max_lat }  — from the /analyze API response
 *   areaHa:           claimed area in hectares
 *   referenceGeojson: GeoJSON FeatureCollection of scrub/forest/plantation polygons from OSM
 */

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

interface Bbox {
  min_lon: number;
  min_lat: number;
  max_lon: number;
  max_lat: number;
}

interface SatelliteMapProps {
  bbox: Bbox;
  areaHa?: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  referenceGeojson?: any;
}

// ── Land-cover type → colour mapping ─────────────────────────────────────────
function getLandCoverStyle(feature: GeoJSON.Feature): L.PathOptions {
  const tags = (feature.properties ?? {}) as Record<string, string>;
  const landuse   = (tags.forest_type ?? "").toLowerCase();
  const natural   = (tags.natural ?? "").toLowerCase();

  // Plantation / orchard / nursery — company-run forestation (teal/cyan)
  if (["plantation", "plant_nursery", "orchard", "vineyard"].includes(landuse)) {
    return { color: "#22d3ee", weight: 1.5, fillColor: "#22d3ee", fillOpacity: 0.35 };
  }
  // Dense natural forest / wood (dark green)
  if (natural === "wood" || landuse === "forest") {
    return { color: "#16a34a", weight: 1.5, fillColor: "#16a34a", fillOpacity: 0.35 };
  }
  // Scrub / grassland (yellow-green)
  if (["scrub", "grassland"].includes(natural)) {
    return { color: "#a3e635", weight: 1.5, fillColor: "#a3e635", fillOpacity: 0.30 };
  }
  // Fallback (olive)
  return { color: "#84cc16", weight: 1.5, fillColor: "#84cc16", fillOpacity: 0.25 };
}

function getLandCoverLabel(feature: GeoJSON.Feature): string {
  const tags = (feature.properties ?? {}) as Record<string, string>;
  const name    = tags.name ?? "";
  const ft      = (tags.forest_type ?? "").replace(/_/g, " ");
  const natural = (tags.natural ?? "").replace(/_/g, " ");
  const label   = name || ft || natural || "Vegetation";
  const src     = tags.source ?? "OpenStreetMap";
  return `<strong style="text-transform:capitalize">${label}</strong><br/><span style="color:#888;font-size:11px">Source: ${src}</span>`;
}

export default function SatelliteMap({ bbox, areaHa, referenceGeojson }: SatelliteMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    // Centre on bbox centroid
    const centerLat = (bbox.min_lat + bbox.max_lat) / 2;
    const centerLon = (bbox.min_lon + bbox.max_lon) / 2;

    const map = L.map(mapContainerRef.current, {
      center: [centerLat, centerLon],
      zoom: 12,
      zoomControl: true,
      scrollWheelZoom: false,
      attributionControl: true,
    });
    mapRef.current = map;

    // ESRI World Imagery — satellite tiles, free, no API key
    L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      {
        attribution:
          "Tiles © Esri — Source: Esri, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, GIS User Community",
        maxZoom: 18,
      }
    ).addTo(map);

    // ESRI World Boundaries and Places labels (overlay on top of satellite)
    L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 18, opacity: 0.7 }
    ).addTo(map);

    // ── Reference land-cover polygons (scrub / forest / plantation) ──────────
    if (referenceGeojson && referenceGeojson.features?.length > 0) {
      L.geoJSON(referenceGeojson, {
        style: getLandCoverStyle,
        onEachFeature: (feature, layer) => {
          layer.bindPopup(getLandCoverLabel(feature), { maxWidth: 220 });
        },
      }).addTo(map);
    }

    // ── Claimed KMZ boundary (bright blue dashed rectangle — distinct from green reference polygons)
    const bounds: L.LatLngBoundsExpression = [
      [bbox.min_lat, bbox.min_lon],
      [bbox.max_lat, bbox.max_lon],
    ];

    const rect = L.rectangle(bounds, {
      color: "#38bdf8",         // sky-blue — stands out from green OSM polygons
      weight: 3,
      opacity: 1,
      dashArray: "8, 6",       // dashed border for extra distinction
      fillColor: "#38bdf8",
      fillOpacity: 0.08,
    }).addTo(map);

    rect.bindPopup(
      `<div style="font-family:system-ui;font-size:13px;line-height:1.6">
        <strong>Claimed Project Area</strong><br/>
        ${areaHa != null ? `<span>${areaHa.toFixed(1)} ha (from KMZ)</span><br/>` : ""}
        <span style="color:#888;font-size:11px">
          ${bbox.min_lat.toFixed(5)}°N, ${bbox.min_lon.toFixed(5)}°E
        </span>
      </div>`,
      { maxWidth: 200 }
    );

    // Fit the map to the bbox
    map.fitBounds(bounds, { padding: [40, 40] });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [bbox, areaHa, referenceGeojson]);

  return (
    <div
      ref={mapContainerRef}
      style={{ height: "400px", width: "100%", borderRadius: "0.75rem", overflow: "hidden" }}
    />
  );
}
