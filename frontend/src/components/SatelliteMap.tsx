/**
 * SatelliteMap.tsx — Leaflet map showing the claimed KMZ bbox on real satellite imagery.
 * Uses ESRI World Imagery tiles (free, no API key required).
 *
 * Props:
 *   bbox: { min_lon, min_lat, max_lon, max_lat }  — from the /analyze API response
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
}

export default function SatelliteMap({ bbox, areaHa }: SatelliteMapProps) {
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

    // Draw the claimed bbox rectangle
    const bounds: L.LatLngBoundsExpression = [
      [bbox.min_lat, bbox.min_lon],
      [bbox.max_lat, bbox.max_lon],
    ];

    const rect = L.rectangle(bounds, {
      color: "#4ade80",       // trust-green-glow
      weight: 2.5,
      opacity: 0.95,
      fillColor: "#4ade80",
      fillOpacity: 0.12,
    }).addTo(map);

    // Popup on the rectangle
    rect.bindPopup(
      `<div style="font-family:system-ui;font-size:13px;line-height:1.6">
        <strong>Claimed Area</strong><br/>
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
  }, [bbox, areaHa]);

  return (
    <div
      ref={mapContainerRef}
      style={{ height: "400px", width: "100%", borderRadius: "0.75rem", overflow: "hidden" }}
    />
  );
}
