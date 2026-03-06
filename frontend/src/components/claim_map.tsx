/**
 * ClaimMap.tsx — Unified satellite map with KMZ claim overlay and reference land-cover.
 *
 * Features:
 *   • KMZ file upload → /analyze API call
 *   • ESRI World Imagery satellite base layer (matches real-world vegetation)
 *   • Reference land-cover overlays: forest (green), plantation (cyan), scrub (yellow-green)
 *   • Claimed project boundary as dashed blue rectangle
 *   • Layer toggle + legend + bound-fitting
 *
 * Uses Leaflet with dynamic import to avoid SSR issues.
 */

import { useEffect, useRef, useState } from "react";

interface Bbox {
  min_lon: number;
  min_lat: number;
  max_lon: number;
  max_lat: number;
}

interface MapData {
  bbox: Bbox;
  claimed_hectares: number;
  verified_hectares: number;
  overlap_percent: number;
  protected_area_overlap_ha: number;
  reference_geojson?: GeoJSON.FeatureCollection;
  claimed_polygon_geojson?: GeoJSON.FeatureCollection;
}

interface ClaimMapProps {
  kmzFile: File | null;
  /** Called once map data is loaded */
  onLoaded?: (data: MapData) => void;
}

// ── Land-cover type → colour mapping for reference GeoJSON polygons ──
function getLandCoverStyle(feature: GeoJSON.Feature): any {
  const tags = (feature.properties ?? {}) as Record<string, string>;
  const landuse = (tags.forest_type ?? "").toLowerCase();
  const natural = (tags.natural ?? "").toLowerCase();

  // Plantation / orchard / nursery — company-run forestation (teal/cyan)
  if (["plantation", "plant_nursery", "orchard", "vineyard"].includes(landuse)) {
    return { color: "#22d3ee", weight: 1.5, fillColor: "#22d3ee", fillOpacity: 0.4 };
  }
  // Dense natural forest / wood (dark green)
  if (natural === "wood" || landuse === "forest") {
    return { color: "#16a34a", weight: 1.5, fillColor: "#16a34a", fillOpacity: 0.4 };
  }
  // Scrub / grassland (yellow-green)
  if (["scrub", "grassland"].includes(natural)) {
    return { color: "#a3e635", weight: 1.5, fillColor: "#a3e635", fillOpacity: 0.35 };
  }
  // Fallback (olive)
  return { color: "#84cc16", weight: 1.5, fillColor: "#84cc16", fillOpacity: 0.3 };
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

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export function ClaimMap({ kmzFile, onLoaded }: ClaimMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null); // L.Map instance
  const [status, setStatus] = useState<"idle" | "loading" | "loaded" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [mapData, setMapData] = useState<MapData | null>(null);
  const [showRefLayer, setShowRefLayer] = useState(true);

  // Fetch analysis data from /analyze endpoint when KMZ changes
  useEffect(() => {
    if (!kmzFile) return;

    setStatus("loading");
    setError(null);

    const form = new FormData();
    form.append("kmz_file", kmzFile);
    form.append("company_claim", "");

    fetch(`${API_BASE}/analyze`, { method: "POST", body: form })
      .then((res) => {
        if (!res.ok) {
          return res.json().then((e: any) => {
            throw new Error(e.detail ?? `HTTP ${res.status}`);
          });
        }
        return res.json() as Promise<any>;
      })
      .then((analysisData) => {
        // Transform /analyze response into MapData
        const mapData: MapData = {
          bbox: analysisData.bbox || { min_lon: 0, min_lat: 0, max_lon: 0, max_lat: 0 },
          claimed_hectares: analysisData.claimed_hectares || 0,
          verified_hectares: analysisData.verified_hectares || 0,
          overlap_percent: analysisData.overlap_percent || 0,
          protected_area_overlap_ha: analysisData.protected_area_overlap_ha || 0,
          reference_geojson: analysisData.reference_geojson,
          claimed_polygon_geojson: analysisData.claimed_polygon_geojson,
        };
        setMapData(mapData);
        setStatus("loaded");
        onLoaded?.(mapData);
      })
      .catch((e) => {
        setError(e.message);
        setStatus("error");
      });
  }, [kmzFile, onLoaded]);

  // Initialize Leaflet map with satellite base + reference overlays
  useEffect(() => {
    if (status !== "loaded" || !mapData || !mapContainerRef.current) return;

    import("leaflet").then((L) => {
      // Fix default marker icons
      // @ts-expect-error leaflet internal
      delete L.Icon.Default.prototype._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
        iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
        shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      });

      // Destroy old map if re-rendering
      if (mapRef.current) {
        (mapRef.current as L.Map).remove();
        mapRef.current = null;
      }

      const centerLat = (mapData.bbox.min_lat + mapData.bbox.max_lat) / 2;
      const centerLon = (mapData.bbox.min_lon + mapData.bbox.max_lon) / 2;

      const map = L.map(mapContainerRef.current!, {
        center: [centerLat, centerLon],
        zoom: 12,
        zoomControl: true,
        scrollWheelZoom: false,
        attributionControl: true,
      });

      // ── Base layers ──────────────────────────────────────────────────────
      const osmLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap contributors",
        maxZoom: 18,
      });

      // ESRI World Imagery — satellite tiles, free, no API key (PRIMARY)
      const satelliteLayer = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        {
          attribution:
            "Tiles © Esri — Source: Esri, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, GIS User Community",
          maxZoom: 18,
        }
      );

      // ESRI World Boundaries and Places labels (overlay on top of satellite)
      const labelsLayer = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        { maxZoom: 18, opacity: 0.7 }
      );

      // Add satellite + labels as default
      satelliteLayer.addTo(map);
      labelsLayer.addTo(map);

      // Base layer control
      const baseLayers = {
        "🛰️ Satellite": satelliteLayer,
        "🗺️ Street Map": osmLayer,
      };

      // ── Reference land-cover polygons (forest/plantation/scrub) ──────────
      let overlayLayers: Record<string, L.GeoJSON> = {};

      if (mapData.reference_geojson && mapData.reference_geojson.features?.length > 0) {
        const refLayer = L.geoJSON(mapData.reference_geojson, {
          style: getLandCoverStyle,
          onEachFeature: (feature, layer) => {
            layer.bindPopup(getLandCoverLabel(feature), { maxWidth: 220 });
          },
        }).addTo(map);

        overlayLayers["🌲 Land Cover (OSM)"] = refLayer;
      }

      // ── Claimed area boundary (actual polygon if available, else bounding box) ────
      const bounds: L.LatLngBoundsExpression = [
        [mapData.bbox.min_lat, mapData.bbox.min_lon],
        [mapData.bbox.max_lat, mapData.bbox.max_lon],
      ];

      let claimedLayerGroup: L.FeatureGroup | null = null;

      if (mapData.claimed_polygon_geojson && mapData.claimed_polygon_geojson.features?.length > 0) {
        // Display actual polygon from KMZ file
        const claimedGeoJson = L.geoJSON(mapData.claimed_polygon_geojson, {
          style: {
            color: "#38bdf8",       // sky-blue
            weight: 3,
            opacity: 1,
            dashArray: "8, 6",      // dashed border
            fillColor: "#38bdf8",
            fillOpacity: 0.08,
          },
          onEachFeature: (feature, layer) => {
            layer.bindPopup(
              `<div style="font-family:system-ui;font-size:13px;line-height:1.6">
                <strong>Claimed Project Area (KMZ Polygon)</strong><br/>
                <span>${mapData.claimed_hectares.toFixed(1)} ha claimed</span><br/>
                <span style="color:#22c55e">${mapData.verified_hectares.toFixed(1)} ha verified</span><br/>
                <span style="${mapData.protected_area_overlap_ha > 0 ? 'color:#f97316' : 'color:#888'}">
                  ${mapData.protected_area_overlap_ha > 0 ? `⚠ ${mapData.protected_area_overlap_ha.toFixed(1)} ha in protected area` : "✓ No protected area overlap"}
                </span>
              </div>`,
              { maxWidth: 240 }
            );
          },
        }).addTo(map);

        claimedLayerGroup = claimedGeoJson;
      } else {
        // Fallback: draw bounding box rectangle if no polygon available
        const claimRect = L.rectangle(bounds, {
          color: "#38bdf8",       // sky-blue
          weight: 3,
          opacity: 1,
          dashArray: "8, 6",      // dashed border
          fillColor: "#38bdf8",
          fillOpacity: 0.08,
        }).addTo(map);

        claimRect.bindPopup(
          `<div style="font-family:system-ui;font-size:13px;line-height:1.6">
            <strong>Claimed Project Area (Bounding Box)</strong><br/>
            <span>${mapData.claimed_hectares.toFixed(1)} ha claimed (from KMZ)</span><br/>
            <span style="color:#22c55e">${mapData.verified_hectares.toFixed(1)} ha verified</span><br/>
            <span style="${mapData.protected_area_overlap_ha > 0 ? 'color:#f97316' : 'color:#888'}">
              ${mapData.protected_area_overlap_ha > 0 ? `⚠ ${mapData.protected_area_overlap_ha.toFixed(1)} ha in protected area` : "✓ No protected area overlap"}
            </span><br/>
            <span style="color:#888;font-size:11px">
              ${mapData.bbox.min_lat.toFixed(5)}°N, ${mapData.bbox.min_lon.toFixed(5)}°E
            </span>
          </div>`,
          { maxWidth: 240 }
        );

        claimedLayerGroup = claimRect as any;
      }

      if (claimedLayerGroup) {
        overlayLayers["📍 Claimed Area (KMZ)"] = claimedLayerGroup as any;
      }

      // ── Layer control ────────────────────────────────────────────────────
      L.control.layers(baseLayers, overlayLayers, { position: "topright" }).addTo(map);

      // Fit map to claimed area bounds (polygon if available, else bbox)
      let fitBounds: L.LatLngBoundsExpression;
      if (claimedLayerGroup && (claimedLayerGroup as any).getBounds) {
        fitBounds = (claimedLayerGroup as any).getBounds();
      } else {
        fitBounds = [
          [mapData.bbox.min_lat, mapData.bbox.min_lon],
          [mapData.bbox.max_lat, mapData.bbox.max_lon],
        ];
      }
      map.fitBounds(fitBounds, { padding: [40, 40] });

      mapRef.current = map;
    });

    return () => {
      if (mapRef.current) {
        (mapRef.current as L.Map).remove();
        mapRef.current = null;
      }
    };
  }, [status, mapData]);

  // ── Render ──────────────────────────────────────────────────────────────────
  if (!kmzFile) return null;

  return (
    <div className="rounded-xl border border-border bg-gradient-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">🗺️ Satellite Map</span>
          {status === "loading" && (
            <span className="text-xs text-muted-foreground animate-pulse">Analyzing…</span>
          )}
          {status === "loaded" && (
            <span className="text-xs text-emerald-400">Ready</span>
          )}
        </div>

        {/* Legend */}
        {status === "loaded" && mapData && (
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <span className="w-3 h-3" style={{ backgroundColor: "#38bdf8", borderRadius: "2px" }} />
              Claimed Area
            </div>
            {mapData.verified_hectares > 0 && (
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <span className="w-3 h-3" style={{ backgroundColor: "#16a34a", borderRadius: "2px" }} />
                Forest
              </div>
            )}
            {mapData.protected_area_overlap_ha > 0 && (
              <div className="flex items-center gap-1.5 text-orange-400 font-medium">
                <span className="w-3 h-3" style={{ backgroundColor: "#f97316", borderRadius: "2px" }} />
                Protected Area
              </div>
            )}
          </div>
        )}
      </div>

      {/* Map container */}
      {status === "error" ? (
        <div className="h-64 flex items-center justify-center text-sm text-red-400">
          ⚠ Map failed: {error}
        </div>
      ) : status === "loading" ? (
        <div className="h-64 flex items-center justify-center text-sm text-muted-foreground animate-pulse">
          Fetching analysis + satellite imagery…
        </div>
      ) : (
        <>
          {/* Leaflet CSS */}
          <link
            rel="stylesheet"
            href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          />
          <div
            ref={mapContainerRef}
            className="w-full"
            style={{ height: "480px" }}
          />
        </>
      )}

      {/* Stats below map */}
      {status === "loaded" && mapData && (
        <div className="px-5 py-4 border-t border-border grid grid-cols-2 gap-4 text-sm">
          <div className="flex flex-col gap-1">
            <span className="text-muted-foreground">Claimed Area</span>
            <span className="font-semibold text-lg">{mapData.claimed_hectares.toFixed(1)} ha</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-muted-foreground">Verified Forest</span>
            <span className="font-semibold text-lg text-emerald-400">{mapData.verified_hectares.toFixed(1)} ha</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-muted-foreground">Overlap</span>
            <span className="font-semibold">{mapData.overlap_percent.toFixed(1)}%</span>
          </div>
          {mapData.protected_area_overlap_ha > 0 && (
            <div className="flex flex-col gap-1">
              <span className="text-orange-400 text-muted-foreground">⚠ Protected Area</span>
              <span className="font-semibold text-orange-400">{mapData.protected_area_overlap_ha.toFixed(1)} ha</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ClaimMap;