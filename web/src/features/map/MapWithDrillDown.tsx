"use client";

/**
 * MapWithDrillDown — client wrapper around RiskMapPanel + RegionDrillDown.
 *
 * Responsibilities:
 *   1. Reads seasonKey from the Zustand store (map page is a Server Component
 *      so it cannot read client state directly).
 *   2. Manages drillRegion local state (separate from store.mapDrillRegion
 *      so map-page drill state doesn't bleed into the forecast page).
 *   3. Passes season + onRegionClick + drillRegion + onBack to RiskMapPanel.
 *      RiskMapPanel handles:
 *        - Region choropleth (default view)
 *        - Zone choropleth + fly-to (drill-down view)
 *        - "← All Regions" button inside the map
 *   4. Shows RegionDrillDown table below the map when a region is selected
 *      (provides detailed zone stats: prob bars, RO-HSS, tier).
 */

import dynamic from "next/dynamic";
import { useState, useCallback } from "react";
import { useSelectionStore } from "@/store/selectionStore";
import { REGION_DISPLAY } from "@/constants/regions";
import { RegionDrillDown } from "./RegionDrillDown";
import type { SeasonKey } from "@/types/forecast";

// Leaflet requires a browser environment — load dynamically with SSR disabled.
const RiskMapPanel = dynamic(
  () => import("./RiskMapPanel").then((m) => ({ default: m.RiskMapPanel })),
  { ssr: false, loading: () => <MapSkeleton /> }
);

function MapSkeleton() {
  return (
    <div className="h-[360px] sm:h-[480px] md:h-[500px] w-full rounded-xl border border-background-border bg-background-surface animate-pulse flex items-center justify-center">
      <span className="text-sm text-text-muted">Loading map…</span>
    </div>
  );
}

export function MapWithDrillDown() {
  const seasonKey = useSelectionStore((s) => s.seasonKey);

  // Which region (if any) is currently drilled into
  const [drillRegion, setDrillRegion] = useState<string | null>(null);

  const handleRegionClick = useCallback((regionKey: string) => {
    // Toggle: click same region again to close, click different region to switch
    setDrillRegion((prev) => (prev === regionKey ? null : regionKey));
  }, []);

  const handleBack = useCallback(() => setDrillRegion(null), []);

  const drillDisplay = drillRegion
    ? (REGION_DISPLAY[drillRegion as keyof typeof REGION_DISPLAY] ?? drillRegion)
    : null;

  return (
    <div className="flex flex-col gap-0">
      {/* Map — handles both region and zone views internally */}
      <div className="rounded-xl overflow-hidden border border-background-border">
        <RiskMapPanel
          season={seasonKey as SeasonKey}
          onRegionClick={handleRegionClick}
          drillRegion={drillRegion}
          onBack={handleBack}
        />
      </div>

      {/* Click-hint — shown before any region is selected */}
      {!drillRegion && (
        <p className="text-xs text-text-faint text-center mt-2">
          Click a region to drill into zone-level forecasts ↓
        </p>
      )}

      {/* Zone breakdown table — shown below map when drilling */}
      {drillRegion && drillDisplay && (
        <RegionDrillDown
          regionKey={drillRegion}
          regionDisplay={drillDisplay}
          season={seasonKey as SeasonKey}
          onClose={handleBack}
        />
      )}
    </div>
  );
}
