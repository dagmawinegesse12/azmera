"use client";

import { REGION_OPTIONS } from "@/constants/regions";
import { FORECAST_SEASONS } from "@/constants/seasons";
import { useSelectionStore } from "@/store/selectionStore";
import { ZoneSelector } from "./ZoneSelector";

export function RegionSeasonSelector() {
  const regionKey   = useSelectionStore((s) => s.regionKey);
  const season      = useSelectionStore((s) => s.seasonKey);
  const setRegion   = useSelectionStore((s) => s.setRegion);
  const setSeason   = useSelectionStore((s) => s.setSeason);
  const requestForecast = useSelectionStore((s) => s.requestForecast);

  const canGenerate = Boolean(regionKey);

  return (
    <div className="flex flex-col sm:flex-row sm:flex-wrap gap-3 sm:gap-4 sm:items-end">

      {/* Region selector */}
      <div className="flex flex-col gap-1.5">
        <label
          htmlFor="region-select"
          className="text-xs font-medium uppercase tracking-wider"
          style={{ color: "var(--text-muted)" }}
        >
          Region
        </label>
        <select
          id="region-select"
          value={regionKey ?? ""}
          onChange={(e) => setRegion(e.target.value)}
          className="rounded-lg px-3 py-2 text-sm w-full sm:w-48 border outline-none focus:ring-2 transition-shadow"
          style={{
            background:  "var(--background-elevated)",
            borderColor: "var(--background-border)",
            color:       regionKey ? "var(--text-primary)" : "var(--text-faint)",
          }}
        >
          <option value="" style={{ color: "var(--text-faint)" }}>
            Select region…
          </option>
          {REGION_OPTIONS.map((r) => (
            <option
              key={r.key}
              value={r.key}
              style={{ color: "var(--text-primary)", background: "var(--background-elevated)" }}
            >
              {r.label}
            </option>
          ))}
        </select>
      </div>

      {/* Season selector */}
      <div className="flex flex-col gap-1.5">
        <label
          htmlFor="season-select"
          className="text-xs font-medium uppercase tracking-wider"
          style={{ color: "var(--text-muted)" }}
        >
          Season
        </label>
        <select
          id="season-select"
          value={season}
          onChange={(e) => setSeason(e.target.value as "Kiremt" | "Belg")}
          className="rounded-lg px-3 py-2 text-sm w-full sm:w-48 border outline-none focus:ring-2 transition-shadow"
          style={{
            background:  "var(--background-elevated)",
            borderColor: "var(--background-border)",
            color:       "var(--text-primary)",
          }}
        >
          {FORECAST_SEASONS.map((s) => (
            <option
              key={s.key}
              value={s.key}
              style={{ background: "var(--background-elevated)" }}
            >
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {/* Zone selector — rendered only when a region is selected.
          Fetches zone list and shows Region | Zone toggle + zone dropdown. */}
      {regionKey && <ZoneSelector />}

      {/* Generate button */}
      <button
        type="button"
        onClick={requestForecast}
        disabled={!canGenerate}
        className="w-full sm:w-auto rounded-lg px-6 py-2 text-sm font-medium text-white transition-all duration-200 hover:brightness-110 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:brightness-100"
        style={{ background: "var(--accent-green)" }}
      >
        Generate Forecast
      </button>
    </div>
  );
}
