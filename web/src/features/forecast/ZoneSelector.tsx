"use client";

/**
 * ZoneSelector — "Region | Zone" mode toggle + zone dropdown.
 *
 * Rendered inside RegionSeasonSelector when a region is selected.
 * On zone selection, calls store.setZone(key, display).
 * On "Region" mode, calls store.setZone(null) to clear.
 */

import { useSelectionStore } from "@/store/selectionStore";
import { useRegionZones } from "@/hooks/useForecast";
import { useLocale } from "@/hooks/useLocale";

export function ZoneSelector() {
  const regionKey  = useSelectionStore((s) => s.regionKey);
  const zoneKey    = useSelectionStore((s) => s.zoneKey);
  const setZone    = useSelectionStore((s) => s.setZone);

  const { data: zones, isLoading } = useRegionZones(regionKey);
  const t = useLocale();

  // No zones for this region — don't render anything
  if (!isLoading && (!zones || zones.length === 0)) return null;

  const isZoneMode = zoneKey !== null;

  return (
    <div className="flex flex-col gap-1.5">
      {/* Mode toggle */}
      <label className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
        {t.zoneSelector.levelLabel}
      </label>
      <div className="flex items-center rounded-lg overflow-hidden border text-xs font-medium"
           style={{ borderColor: "var(--background-border)" }}>
        <button
          type="button"
          onClick={() => setZone(null)}
          aria-pressed={!isZoneMode}
          className="px-3 py-2 transition-colors"
          style={{
            background:  !isZoneMode ? "var(--background-surface)" : "var(--background-elevated)",
            color:       !isZoneMode ? "var(--text-primary)"        : "var(--text-muted)",
          }}
        >
          {t.zoneSelector.regionButton}
        </button>
        <button
          type="button"
          onClick={() => {
            // Switch to zone mode — if zones already loaded, pre-select first
            if (zones && zones.length > 0 && !isZoneMode) {
              setZone(zones[0].zone_key, zones[0].zone_display);
            }
          }}
          aria-pressed={isZoneMode}
          disabled={isLoading}
          className="px-3 py-2 transition-colors disabled:opacity-50"
          style={{
            background:  isZoneMode ? "var(--background-surface)" : "var(--background-elevated)",
            color:       isZoneMode ? "var(--text-primary)"       : "var(--text-muted)",
          }}
        >
          {isLoading ? "…" : t.zoneSelector.zoneButton}
        </button>
      </div>

      {/* Zone dropdown — only when in zone mode */}
      {isZoneMode && zones && zones.length > 0 && (
        <select
          id="zone-select"
          value={zoneKey ?? ""}
          onChange={(e) => {
            const selected = zones.find((z) => z.zone_key === e.target.value);
            if (selected) setZone(selected.zone_key, selected.zone_display);
          }}
          className="rounded-lg px-3 py-2 text-sm w-full sm:w-52 border outline-none focus:ring-2 transition-shadow mt-1"
          style={{
            background:  "var(--background-elevated)",
            borderColor: "var(--background-border)",
            color:       "var(--text-primary)",
          }}
        >
          {zones.map((z) => (
            <option
              key={z.zone_key}
              value={z.zone_key}
              style={{ background: "var(--background-elevated)", color: "var(--text-primary)" }}
            >
              {z.zone_display}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
