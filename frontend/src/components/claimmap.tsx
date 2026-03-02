// src/components/ClaimMap.tsx
// Interactive map showing three polygon layers:
//   RED    — claimed area (what the company submitted)
//   GREEN  — verified forest intersection (what reference data confirms)
//   ORANGE — protected area overlaps (automatic disqualifiers)
//
// Uses Leaflet via react-leaflet. Install if needed:
//   npm install leaflet react-leaflet
//   npm install -D @types/leaflet

import { useEffect, useRef, useState } from "react";

interface MapFeature {
  type: "Feature";
  properties: {
    layer: "claimed" | "verified" | "protected";
    label: string;
    color: string;
  };
  geometry: object;
}

interface MapData {
  type: "FeatureCollection";
  features: MapFeature[];
  center: { lat: number; lon: number };
  bbox: { min_lat: number; max_lat: number; min_lon: number; max_lon: number };
}

interface ClaimMapProps {
  kmzFile: File | null;
  /** Called once map data is loaded, to let parent know it's ready */
  onLoaded?: (data: MapData) => void;
}

const LAYER_STYLE = {
  claimed:   { color: "#ef4444", fillColor: "#ef4444", fillOpacity: 0.15, weight: 2 },
  verified:  { color: "#22c55e", fillColor: "#22c55e", fillOpacity: 0.25, weight: 2 },
  protected: { color: "#f97316", fillColor: "#f97316", fillOpacity: 0.20, weight: 2, dashArray: "6 4" },
};

const LEGEND = [
  { color: "#ef4444", label: "Claimed area" },
  { color: "#22c55e", label: "Verified forest" },
  { color: "#f97316", label: "Protected area" },
];

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export function ClaimMap({ kmzFile, onLoaded }: ClaimMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef          = useRef<unknown>(null);  // L.Map instance
  const [status, setStatus]   = useState<"idle" | "loading" | "loaded" | "error">("idle");
  const [error, setError]     = useState<string | null>(null);
  const [mapData, setMapData] = useState<MapData | null>(null);

  // Fetch map GeoJSON from backend whenever KMZ changes
  useEffect(() => {
    if (!kmzFile) return;

    setStatus("loading");
    setError(null);

    const form = new FormData();
    form.append("kmz_file", kmzFile);

    fetch(`${API_BASE}/map`, { method: "POST", body: form })
      .then((res) => {
        if (!res.ok) return res.json().then((e) => { throw new Error(e.detail ?? `HTTP ${res.status}`); });
        return res.json() as Promise<MapData>;
      })
      .then((data) => {
        setMapData(data);
        setStatus("loaded");
        onLoaded?.(data);
      })
      .catch((e) => {
        setError(e.message);
        setStatus("error");
      });
  }, [kmzFile]);

  // Initialize Leaflet map once container exists
  useEffect(() => {
    if (status !== "loaded" || !mapData || !mapContainerRef.current) return;

    // Dynamically import Leaflet to avoid SSR issues
    import("leaflet").then((L) => {
      // Fix default marker icons (Leaflet + bundler issue)
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

      const map = L.map(mapContainerRef.current!, {
        center: [mapData.center.lat, mapData.center.lon],
        zoom: 10,
        zoomControl: true,
      });

      // Base tile layer — OpenStreetMap
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap contributors",
        maxZoom: 18,
      }).addTo(map);

      // Add satellite layer toggle
      const satellite = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        { attribution: "Esri", maxZoom: 18 }
      );

      const baseLayers = {
        "Street Map": L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          attribution: "© OpenStreetMap contributors",
        }),
        "Satellite": satellite,
      };

      // Add GeoJSON layers — order matters: protected first, then claimed, then verified on top
      const layerOrder = ["protected", "claimed", "verified"] as const;
      const bounds: L.LatLngBounds[] = [];

      const overlayLayers: Record<string, L.GeoJSON> = {};

      for (const layerName of layerOrder) {
        const features = mapData.features.filter((f) => f.properties.layer === layerName);
        if (features.length === 0) continue;

        const geojsonLayer = L.geoJSON(
          { type: "FeatureCollection", features } as GeoJSON.FeatureCollection,
          {
            style: () => LAYER_STYLE[layerName],
            onEachFeature(feature, layer) {
              layer.bindPopup(
                `<div style="font-family:monospace;font-size:12px">
                  <b>${feature.properties.label}</b><br/>
                  <span style="color:${feature.properties.color}">● ${layerName}</span>
                </div>`
              );
            },
          }
        ).addTo(map);

        bounds.push(geojsonLayer.getBounds());

        const labels: Record<string, string> = {
          claimed:   "🔴 Claimed Area",
          verified:  "🟢 Verified Forest",
          protected: "🟠 Protected Area",
        };
        overlayLayers[labels[layerName]] = geojsonLayer;
      }

      // Layer control
      L.control.layers(baseLayers, overlayLayers, { position: "topright" }).addTo(map);

      // Fit map to claimed polygon bounds
      if (bounds.length > 0) {
        const combined = bounds.reduce((acc, b) => acc.extend(b));
        map.fitBounds(combined, { padding: [40, 40] });
      }

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
          <span className="text-sm font-semibold">Claim Map</span>
          {status === "loading" && (
            <span className="text-xs text-muted-foreground animate-pulse">Loading…</span>
          )}
          {status === "loaded" && (
            <span className="text-xs text-emerald-400">
              {mapData?.features.length ?? 0} layers
            </span>
          )}
        </div>

        {/* Legend */}
        {status === "loaded" && (
          <div className="flex items-center gap-4">
            {LEGEND.map(({ color, label }) => {
              const hasLayer = mapData?.features.some((f) => f.properties.color === color);
              if (!hasLayer) return null;
              return (
                <div key={label} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="w-3 h-3 rounded-sm inline-block" style={{ backgroundColor: color, opacity: 0.7 }} />
                  {label}
                </div>
              );
            })}
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
          Loading map data…
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
            style={{ height: "420px" }}
          />
        </>
      )}

      {/* Stats below map */}
      {status === "loaded" && mapData && (
        <div className="px-5 py-3 border-t border-border flex gap-6 text-xs text-muted-foreground">
          <span>
            Center: {mapData.center.lat.toFixed(4)}°N, {mapData.center.lon.toFixed(4)}°E
          </span>
          <span>
            Bbox: {mapData.bbox.min_lat.toFixed(3)}–{mapData.bbox.max_lat.toFixed(3)}°N,{" "}
            {mapData.bbox.min_lon.toFixed(3)}–{mapData.bbox.max_lon.toFixed(3)}°E
          </span>
          {mapData.features.some((f) => f.properties.layer === "protected") && (
            <span className="text-orange-400 font-medium">⚠ Protected area overlap detected</span>
          )}
        </div>
      )}
    </div>
  );
}

export default ClaimMap;