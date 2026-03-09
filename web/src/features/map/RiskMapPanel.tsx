"use client";

// NOTE: Leaflet default icon URL fix would go here in a real setup:
// import L from "leaflet";
// delete (L.Icon.Default.prototype as any)._getIconUrl;
// L.Icon.Default.mergeOptions({ iconUrl: ..., iconRetinaUrl: ..., shadowUrl: ... });
// Skipped here — app does not render default markers on the choropleth.

import "leaflet/dist/leaflet.css";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import L from "leaflet";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import type { Layer, LeafletMouseEvent, PathOptions } from "leaflet";
import type { SeasonKey, ZoneForecastResult } from "@/types/forecast";
import { useAllForecasts, useRegionZoneForecasts } from "@/hooks/useForecast";
import { GEOJSON_TO_AZMERA, REGION_DISPLAY } from "@/constants/regions";
import { formatHss } from "@/utils/format";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Props {
  season: SeasonKey;
  /** Called when user clicks a region in region-mode. */
  onRegionClick?: (regionKey: string) => void;
  /** Which region is currently drilled into (null = region overview). */
  drillRegion?: string | null;
  /** Called when user presses "Back to All Regions". */
  onBack?: () => void;
}

interface ForecastEntry {
  region_key: string;
  prediction: string;
  prob_below: number;
  prob_near: number;
  prob_above: number;
  tier: string;
}

type PredictionKey =
  | "Above Normal"
  | "Near Normal"
  | "Below Normal"
  | "suppressed"
  | "unknown";

// ─── Constants ────────────────────────────────────────────────────────────────

const ETHIOPIA_CENTER: [number, number] = [9.145, 40.489];
const DEFAULT_ZOOM = 6;

const PREDICTION_COLOR: Record<PredictionKey, string> = {
  "Above Normal": "#4caf84",
  "Near Normal":  "#f0c040",
  "Below Normal": "#e05252",
  suppressed:     "#2a3848",
  unknown:        "#1e2a3d",
};

const LEGEND_ITEMS: { label: string; color: string }[] = [
  { label: "Above Normal",           color: PREDICTION_COLOR["Above Normal"] },
  { label: "Near Normal",            color: PREDICTION_COLOR["Near Normal"]  },
  { label: "Below Normal",           color: PREDICTION_COLOR["Below Normal"] },
  { label: "Suppressed / No forecast", color: PREDICTION_COLOR["suppressed"] },
];

const TILE_URL =
  "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const TILE_ATTRIBUTION =
  "\u00a9 <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors \u00a9 <a href='https://carto.com/attributions'>CARTO</a>";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function predictionColor(
  prediction: string | undefined,
  tier: string | undefined
): string {
  if (tier === "suppressed" || !prediction) return PREDICTION_COLOR["suppressed"];
  return PREDICTION_COLOR[prediction as PredictionKey] ?? PREDICTION_COLOR["unknown"];
}

function formatProb(p: number): string {
  return `${Math.round(p * 100)}%`;
}

// ─── Sub-components ──────────────────────────────────────────────────────────

/**
 * Manages map view transitions:
 *  - Resets to Ethiopia overview when drillRegion becomes null.
 *  - Flies to zone bounds when filteredZoneGeojson becomes available.
 */
function MapViewManager({
  drillRegion,
  filteredZoneGeojson,
}: {
  drillRegion: string | null | undefined;
  filteredZoneGeojson: GeoJSON.FeatureCollection | null;
}) {
  const map = useMap();
  const prevDrill = useRef<string | null | undefined>(undefined);

  // On mount: set initial Ethiopia view (no animation).
  useEffect(() => {
    map.setView(ETHIOPIA_CENTER, DEFAULT_ZOOM);
  }, [map]); // eslint-disable-line react-hooks/exhaustive-deps

  // When drillRegion goes from a value to null → fly back to Ethiopia.
  useEffect(() => {
    if (prevDrill.current !== undefined && prevDrill.current !== null && !drillRegion) {
      map.flyTo(ETHIOPIA_CENTER, DEFAULT_ZOOM, { animate: true, duration: 0.8 });
    }
    prevDrill.current = drillRegion;
  }, [map, drillRegion]);

  // When zone GeoJSON loads for a drilled region → fly to its bounds.
  useEffect(() => {
    if (!drillRegion || !filteredZoneGeojson || filteredZoneGeojson.features.length === 0) {
      return;
    }
    try {
      const layer = L.geoJSON(filteredZoneGeojson as GeoJSON.GeoJsonObject);
      const bounds = layer.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [30, 30], maxZoom: 8, animate: true, duration: 0.8 });
      }
    } catch {
      // Ignore bounds errors
    }
  }, [map, drillRegion, filteredZoneGeojson]);

  return null;
}

function LoadingOverlay() {
  return (
    <div className="absolute inset-0 z-[1000] flex items-center justify-center bg-background-card/80 rounded-xl">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 rounded-full border-2 border-sky-500 border-t-transparent animate-spin" />
        <p className="text-sm text-text-muted">Loading map data…</p>
      </div>
    </div>
  );
}

function Legend() {
  return (
    <div className="absolute bottom-4 left-4 z-[1000] rounded-xl border border-background-border bg-background-card/90 backdrop-blur-sm px-3 py-2.5 shadow-lg">
      <p className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
        Forecast
      </p>
      <ul className="space-y-1.5">
        {LEGEND_ITEMS.map((item) => (
          <li key={item.label} className="flex items-center gap-2">
            <span
              className="inline-block h-3 w-3 rounded-sm shrink-0"
              style={{ backgroundColor: item.color }}
            />
            <span className="text-xs text-text-secondary">{item.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function RiskMapPanel({ season, onRegionClick, drillRegion, onBack }: Props) {
  // ── Region GeoJSON (always loaded) ──────────────────────────────────────────
  const [regionGeojson, setRegionGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
  const [geoLoading, setGeoLoading]     = useState(true);
  const [geoError, setGeoError]         = useState(false);

  // State-based key so forecast color updates actually trigger GeoJSON re-mount.
  const [regionGeojsonKey, setRegionGeojsonKey] = useState(0);

  // ── Zone GeoJSON (loaded lazily on first drill-down) ────────────────────────
  const [allZoneGeojson, setAllZoneGeojson]       = useState<GeoJSON.FeatureCollection | null>(null);
  const [zoneGeojsonLoading, setZoneGeojsonLoading] = useState(false);

  // ── Region forecasts (for region choropleth) ────────────────────────────────
  const { data: forecasts, isLoading: forecastLoading } = useAllForecasts(season);

  // ── Zone forecasts (for zone choropleth — enabled only when drilling) ───────
  const { data: zoneForecasts, isLoading: zoneForecastsLoading } = useRegionZoneForecasts(
    drillRegion ?? "",
    season,
    !!drillRegion
  );

  // ── Derived ─────────────────────────────────────────────────────────────────

  const forecastMap = useCallback((): Map<string, ForecastEntry> => {
    const map = new Map<string, ForecastEntry>();
    if (!forecasts) return map;
    for (const entry of forecasts as ForecastEntry[]) {
      map.set(entry.region_key, entry);
    }
    return map;
  }, [forecasts]);

  /** Zone forecasts keyed by zone_key. */
  const zoneForecastMap = useMemo((): Map<string, ZoneForecastResult> => {
    const map = new Map<string, ZoneForecastResult>();
    if (!zoneForecasts) return map;
    for (const z of zoneForecasts) {
      map.set(z.zone_key, z);
    }
    return map;
  }, [zoneForecasts]);

  /** Zone GeoJSON filtered to just the drilled region's features. */
  const filteredZoneGeojson = useMemo((): GeoJSON.FeatureCollection | null => {
    if (!drillRegion || !allZoneGeojson) return null;
    const features = allZoneGeojson.features.filter(
      (f) => f.properties?.region_key === drillRegion
    );
    if (features.length === 0) return null;
    return { ...allZoneGeojson, features };
  }, [drillRegion, allZoneGeojson]);

  const drillDisplay: string | null = drillRegion
    ? (REGION_DISPLAY[drillRegion as keyof typeof REGION_DISPLAY] ?? drillRegion)
    : null;

  // ── Data loading ────────────────────────────────────────────────────────────

  // Fetch region GeoJSON once on mount.
  useEffect(() => {
    setGeoLoading(true);
    fetch("/ethiopia_regions.geojson")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<GeoJSON.FeatureCollection>;
      })
      .then((data) => {
        setRegionGeojson(data);
        setGeoLoading(false);
      })
      .catch(() => {
        setGeoError(true);
        setGeoLoading(false);
      });
  }, []);

  // Fetch zone GeoJSON lazily — only when first drill-down is triggered.
  useEffect(() => {
    if (!drillRegion || allZoneGeojson) return; // already loaded or not needed
    setZoneGeojsonLoading(true);
    fetch("/data/ethiopia_zones.geojson")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<GeoJSON.FeatureCollection>;
      })
      .then((data) => {
        setAllZoneGeojson(data);
        setZoneGeojsonLoading(false);
      })
      .catch(() => {
        setZoneGeojsonLoading(false);
      });
  }, [drillRegion, allZoneGeojson]);

  // Bump region GeoJSON key when forecast data first arrives (forces re-colour).
  useEffect(() => {
    if (forecasts) {
      setRegionGeojsonKey((k) => k + 1);
    }
  }, [forecasts]);

  // ── Loading state ───────────────────────────────────────────────────────────

  const isLoading = drillRegion
    ? zoneGeojsonLoading || zoneForecastsLoading
    : geoLoading || forecastLoading;

  // ── Region layer helpers ────────────────────────────────────────────────────

  const resolveRegionKey = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (props: any): string | undefined =>
      (props?.region_key as string | undefined) ??
      GEOJSON_TO_AZMERA[props?.NAME_1 as string ?? ""],
    []
  );

  const styleRegionFeature = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (feature?: GeoJSON.Feature<GeoJSON.Geometry, any>): PathOptions => {
      const regionKey = resolveRegionKey(feature?.properties);
      const entry = forecastMap().get(regionKey ?? "");
      const fill = predictionColor(entry?.prediction, entry?.tier);
      return {
        fillColor:   fill,
        fillOpacity: 0.65,
        color:       "#0d1520",
        weight:      1,
        opacity:     0.9,
      };
    },
    [forecastMap, resolveRegionKey]
  );

  const onEachRegionFeature = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (feature: GeoJSON.Feature<GeoJSON.Geometry, any>, layer: Layer) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const props = feature.properties as any;
      const regionKey = resolveRegionKey(props);
      const displayName: string =
        (props?.name as string | undefined) ??
        (regionKey ? REGION_DISPLAY[regionKey as keyof typeof REGION_DISPLAY] : undefined) ??
        (props?.NAME_1 as string | undefined) ??
        "Unknown";
      const entry = forecastMap().get(regionKey ?? "");

      const predLabel =
        entry?.tier === "suppressed" ? "Suppressed" : (entry?.prediction ?? "No forecast");

      const probLine =
        entry && entry.tier !== "suppressed"
          ? `<div style="margin-top:4px;font-size:11px;color:#7a90a8">
               Below ${formatProb(entry.prob_below)} &nbsp;|&nbsp;
               Near ${formatProb(entry.prob_near)} &nbsp;|&nbsp;
               Above ${formatProb(entry.prob_above)}
             </div>`
          : "";

      layer.bindTooltip(
        `<div style="font-size:13px;font-weight:600;color:#e2e8f0">${displayName}</div>
         <div style="font-size:12px;color:#94a3b8;margin-top:2px">${predLabel}</div>
         ${probLine}
         <div style="font-size:11px;color:#5a7898;margin-top:4px">Click to view zones ↓</div>`,
        { sticky: true, className: "azmera-tooltip", opacity: 1 }
      );

      layer.on({
        mouseover(e: LeafletMouseEvent) {
          const target = e.target as L.Path;
          target.setStyle({ fillOpacity: 0.85, weight: 2, color: "#4a90d9" });
          target.bringToFront();
        },
        mouseout(e: LeafletMouseEvent) {
          const target = e.target as L.Path;
          target.setStyle({ fillOpacity: 0.65, weight: 1, color: "#0d1520" });
        },
        click() {
          if (onRegionClick && regionKey) {
            onRegionClick(regionKey);
          }
        },
      });
    },
    [forecastMap, onRegionClick, resolveRegionKey]
  );

  // ── Zone layer helpers ──────────────────────────────────────────────────────

  const styleZoneFeature = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (feature?: GeoJSON.Feature<GeoJSON.Geometry, any>): PathOptions => {
      const zoneKey = feature?.properties?.zone_key as string | undefined;
      const entry   = zoneForecastMap.get(zoneKey ?? "");
      const tier    = entry?.no_skill ? "suppressed" : entry?.release_tier;
      const fill    = predictionColor(entry?.prediction, tier);
      return {
        fillColor:   fill,
        fillOpacity: 0.72,
        color:       "#0d1520",
        weight:      1.5,
        opacity:     0.9,
      };
    },
    [zoneForecastMap]
  );

  const onEachZoneFeature = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (feature: GeoJSON.Feature<GeoJSON.Geometry, any>, layer: Layer) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const props    = feature.properties as any;
      const zoneKey  = props?.zone_key  as string | undefined;
      const zoneName = props?.zone_display as string | undefined ?? zoneKey ?? "Unknown";
      const entry    = zoneForecastMap.get(zoneKey ?? "");

      const predLabel = entry?.no_skill
        ? "Suppressed"
        : (entry?.prediction ?? "No forecast");

      const probLine =
        entry && !entry.no_skill
          ? `<div style="margin-top:4px;font-size:11px;color:#7a90a8">
               Below ${formatProb(entry.prob_below)} &nbsp;|&nbsp;
               Near ${formatProb(entry.prob_near)} &nbsp;|&nbsp;
               Above ${formatProb(entry.prob_above)}
             </div>`
          : "";

      const metaLine = entry
        ? `<div style="margin-top:3px;font-size:11px;color:#5a7898">
             ${entry.release_tier} &nbsp;·&nbsp; RO-HSS ${formatHss(entry.ro_hss)}
             ${entry.source === "region_fallback" ? "&nbsp;·&nbsp; ↩ region fallback" : ""}
           </div>`
        : "";

      layer.bindTooltip(
        `<div style="font-size:13px;font-weight:600;color:#e2e8f0">${zoneName}</div>
         <div style="font-size:12px;color:#94a3b8;margin-top:2px">${predLabel}</div>
         ${probLine}${metaLine}`,
        { sticky: true, className: "azmera-tooltip", opacity: 1 }
      );

      layer.on({
        mouseover(e: LeafletMouseEvent) {
          const target = e.target as L.Path;
          target.setStyle({ fillOpacity: 0.92, weight: 2.5, color: "#4a90d9" });
          target.bringToFront();
        },
        mouseout(e: LeafletMouseEvent) {
          const target = e.target as L.Path;
          target.setStyle({ fillOpacity: 0.72, weight: 1.5, color: "#0d1520" });
        },
      });
    },
    [zoneForecastMap]
  );

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="relative h-[360px] sm:h-[480px] md:h-[500px] w-full rounded-xl border border-background-border overflow-hidden">
      {isLoading && <LoadingOverlay />}

      {geoError && (
        <div className="absolute inset-0 z-[999] flex items-center justify-center bg-background-card">
          <p className="text-red-400 text-sm">
            Failed to load region boundaries. Ensure{" "}
            <code className="font-mono text-xs bg-background-elevated px-1 rounded">
              /public/ethiopia_regions.geojson
            </code>{" "}
            is present.
          </p>
        </div>
      )}

      {/* Back to All Regions button — visible only in zone mode */}
      {drillRegion && (
        <div className="absolute top-4 left-14 z-[1000] flex items-center gap-2 pointer-events-none">
          <button
            onClick={onBack}
            className="pointer-events-auto flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-background-card/95 backdrop-blur-sm border border-background-border text-text-primary rounded-lg hover:bg-background-elevated transition-colors shadow-lg"
          >
            ← All Regions
          </button>
          {drillDisplay && (
            <span className="pointer-events-none text-xs text-text-secondary bg-background-card/80 px-2 py-1 rounded-md border border-background-border backdrop-blur-sm">
              {drillDisplay} — Zones
            </span>
          )}
        </div>
      )}

      {/* No-zone fallback message (zone GeoJSON loaded but this region has no features) */}
      {drillRegion && !zoneGeojsonLoading && allZoneGeojson && !filteredZoneGeojson && (
        <div className="absolute inset-x-4 top-16 z-[999] flex items-center justify-center">
          <div className="bg-background-card/90 backdrop-blur-sm border border-background-border rounded-lg px-4 py-3 text-sm text-text-muted shadow-lg">
            No zone boundaries available for{" "}
            <span className="font-semibold text-text-secondary">{drillDisplay}</span>.
            Zone data will appear in the table below.
          </div>
        </div>
      )}

      <MapContainer
        center={ETHIOPIA_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ height: "100%", width: "100%", background: "#0d1520" }}
        zoomControl={true}
        scrollWheelZoom={true}
        attributionControl={true}
      >
        <MapViewManager
          drillRegion={drillRegion}
          filteredZoneGeojson={filteredZoneGeojson}
        />

        <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />

        {/* Region choropleth — shown only when NOT drilling */}
        {!drillRegion && regionGeojson && (
          <GeoJSON
            key={`regions-${regionGeojsonKey}`}
            data={regionGeojson}
            style={styleRegionFeature}
            onEachFeature={onEachRegionFeature}
          />
        )}

        {/* Zone choropleth — shown when drilling AND both geojson + forecasts are loaded */}
        {drillRegion && filteredZoneGeojson && !isLoading && (
          <GeoJSON
            key={`zones-${drillRegion}`}
            data={filteredZoneGeojson}
            style={styleZoneFeature}
            onEachFeature={onEachZoneFeature}
          />
        )}
      </MapContainer>

      {/* Legend — same for both modes */}
      {!geoError && <Legend />}
    </div>
  );
}
