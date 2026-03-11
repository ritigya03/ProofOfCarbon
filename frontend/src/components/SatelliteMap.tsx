/**
 * SatelliteMap.tsx — Single map component showing claimed, verified, and protected
 * areas as tight polygons on satellite imagery. Uses data from /analyze only (no /map).
 *
 * Props:
 *   bbox:                      { min_lon, min_lat, max_lon, max_lat } from analyze
 *   areaHa:                    claimed area in hectares
 *   referenceGeojson:          OSM forest/scrub/plantation polygons (optional overlay)
 *   claimedPolygonGeojson:      GeoJSON FeatureCollection — tight claimed boundary
 *   verifiedIntersectionGeojson: GeoJSON — verified forest (claimed ∩ reference)
 *   protectedOverlapGeojson:   GeoJSON — protected area overlap (disqualifier)
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
  referenceGeojson?: GeoJSON.FeatureCollection;
  claimedPolygonGeojson?: GeoJSON.FeatureCollection;
  verifiedIntersectionGeojson?: GeoJSON.FeatureCollection;
  protectedOverlapGeojson?: GeoJSON.FeatureCollection;
}

const LAYER_STYLE = {
  claimed: {
    color: "#ef4444",
    fillColor: "#ef4444",
    fillOpacity: 0.2,
    weight: 2,
  },
  verified: {
    color: "#22c55e",
    fillColor: "#22c55e",
    fillOpacity: 0.3,
    weight: 2,
  },
  protected: {
    color: "#f97316",
    fillColor: "#f97316",
    fillOpacity: 0.25,
    weight: 2,
    dashArray: "6 4",
  },
  claimedBbox: {
    color: "#38bdf8",
    weight: 3,
    opacity: 1,
    dashArray: "8, 6",
    fillColor: "#38bdf8",
    fillOpacity: 0.08,
  },
};

function getLandCoverStyle(feature: GeoJSON.Feature): L.PathOptions {
  const tags = (feature.properties ?? {}) as Record<string, string>;
  const landuse = (tags.forest_type ?? "").toLowerCase();
  const natural = (tags.natural ?? "").toLowerCase();
  if (["plantation", "plant_nursery", "orchard", "vineyard"].includes(landuse)) {
    return { color: "#22d3ee", weight: 1.5, fillColor: "#22d3ee", fillOpacity: 0.35 };
  }
  if (natural === "wood" || landuse === "forest") {
    return { color: "#16a34a", weight: 1.5, fillColor: "#16a34a", fillOpacity: 0.35 };
  }
  if (["scrub", "grassland"].includes(natural)) {
    return { color: "#a3e635", weight: 1.5, fillColor: "#a3e635", fillOpacity: 0.3 };
  }
  return { color: "#84cc16", weight: 1.5, fillColor: "#84cc16", fillOpacity: 0.25 };
}

function getLandCoverLabel(feature: GeoJSON.Feature): string {
  const tags = (feature.properties ?? {}) as Record<string, string>;
  const name = tags.name ?? "";
  const ft = (tags.forest_type ?? "").replace(/_/g, " ");
  const natural = (tags.natural ?? "").replace(/_/g, " ");
  const label = name || ft || natural || "Vegetation";
  const src = tags.source ?? "OpenStreetMap";
  return `<strong style="text-transform:capitalize">${label}</strong><br/><span style="color:#888;font-size:11px">Source: ${src}</span>`;
}

function addGeoJsonLayer(
  map: L.Map,
  geojson: GeoJSON.FeatureCollection | GeoJSON.Feature,
  style: L.PathOptions,
  label: string,
  popupLabel: string
): L.GeoJSON | null {
  const fc =
    geojson.type === "FeatureCollection"
      ? geojson
      : { type: "FeatureCollection" as const, features: [geojson] };
  if (!fc.features?.length) return null;
  const layer = L.geoJSON(fc, {
    style: () => style,
    onEachFeature(feature, layerInstance) {
      layerInstance.bindPopup(
        `<div style="font-family:system-ui;font-size:12px">${popupLabel}</div>`,
        { maxWidth: 260 }
      );
    },
  });
  layer.addTo(map);
  return layer;
}

export default function SatelliteMap({
  bbox,
  areaHa,
  referenceGeojson,
  claimedPolygonGeojson,
  verifiedIntersectionGeojson,
  protectedOverlapGeojson,
}: SatelliteMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

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

    // Base: ESRI World Imagery (satellite)
    L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      {
        attribution:
          "Tiles © Esri — Source: Esri, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, GIS User Community",
        maxZoom: 18,
      }
    ).addTo(map);

    L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 18, opacity: 0.7 }
    ).addTo(map);

    const bounds: L.LatLngBoundsExpression = [
      [bbox.min_lat, bbox.min_lon],
      [bbox.max_lat, bbox.max_lon],
    ];
    const allBounds: L.LatLngBounds[] = [];

    // 1. Protected overlap (draw first so it sits under claimed/verified)
    if (protectedOverlapGeojson?.features?.length) {
      const layer = addGeoJsonLayer(
        map,
        protectedOverlapGeojson,
        LAYER_STYLE.protected,
        "Protected area overlap",
        "<b>Protected area overlap</b><br/>Land under legal protection — disqualifier for new credits."
      );
      if (layer) allBounds.push(layer.getBounds());
    }

    // 2. Claimed polygon (tight boundary) or bbox rectangle fallback
    if (claimedPolygonGeojson?.features?.length) {
      const layer = addGeoJsonLayer(
        map,
        claimedPolygonGeojson,
        LAYER_STYLE.claimed,
        "Claimed area",
        `<b>Claimed project area</b><br/>${areaHa != null ? `${areaHa.toFixed(1)} ha (from KMZ)` : ""}`
      );
      if (layer) allBounds.push(layer.getBounds());
    } else {
      const rect = L.rectangle(bounds, LAYER_STYLE.claimedBbox).addTo(map);
      rect.bindPopup(
        `<div style="font-family:system-ui;font-size:13px">
          <strong>Claimed Project Area</strong> (bbox)<br/>
          ${areaHa != null ? `<span>${areaHa.toFixed(1)} ha (from KMZ)</span><br/>` : ""}
          <span style="color:#888;font-size:11px">${bbox.min_lat.toFixed(5)}°N, ${bbox.min_lon.toFixed(5)}°E</span>
        </div>`,
        { maxWidth: 200 }
      );
      allBounds.push(rect.getBounds());
    }

    // 3. Verified intersection (tight polygon)
    if (verifiedIntersectionGeojson?.features?.length) {
      const layer = addGeoJsonLayer(
        map,
        verifiedIntersectionGeojson,
        LAYER_STYLE.verified,
        "Verified forest",
        "<b>Verified forest</b><br/>Area where claimed boundary overlaps reference forest data."
      );
      if (layer) allBounds.push(layer.getBounds());
    }

    // 4. Reference land-cover (OSM scrub/forest/plantation) — optional overlay
    if (referenceGeojson?.features?.length) {
      L.geoJSON(referenceGeojson, {
        style: getLandCoverStyle,
        onEachFeature: (feature, layerInstance) => {
          layerInstance.bindPopup(getLandCoverLabel(feature), { maxWidth: 220 });
        },
      }).addTo(map);
    }

    if (allBounds.length > 0) {
      const combined = allBounds.reduce((acc, b) => acc.extend(b));
      map.fitBounds(combined, { padding: [40, 40] });
    } else {
      map.fitBounds(bounds, { padding: [40, 40] });
    }

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [
    bbox,
    areaHa,
    referenceGeojson,
    claimedPolygonGeojson,
    verifiedIntersectionGeojson,
    protectedOverlapGeojson,
  ]);

  return (
    <div
      ref={mapContainerRef}
      style={{ height: "400px", width: "100%", borderRadius: "0.75rem", overflow: "hidden" }}
    />
  );
}
