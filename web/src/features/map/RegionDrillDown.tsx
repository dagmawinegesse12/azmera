"use client";

/**
 * RegionDrillDown — compact panel shown below the risk map when the user
 * clicks a region. Displays all zone forecasts for that region as a table,
 * with tier badges and probability bars.
 *
 * Props:
 *   regionKey     — e.g. "amhara"
 *   regionDisplay — e.g. "Amhara"
 *   season        — e.g. "Kiremt"
 *   onClose       — called when the user dismisses the panel
 */

import { X } from "lucide-react";
import { useRegionZoneForecasts } from "@/hooks/useForecast";
import type { SeasonKey, ZoneForecastResult } from "@/types/forecast";
import { predictionTextClass } from "@/utils/prediction";
import { ZoneSourceBadge } from "@/features/forecast/ZoneSourceBadge";
import { formatHss } from "@/utils/format";

interface Props {
  regionKey:     string;
  regionDisplay: string;
  season:        SeasonKey;
  onClose:       () => void;
}

// ── Prob bar (mini) ───────────────────────────────────────────────────────────
function MiniProbBars({
  below, near, above,
}: {
  below: number; near: number; above: number;
}) {
  const toW = (p: number) => `${Math.round(p * 100)}%`;
  return (
    <div className="flex gap-0.5 h-2 rounded overflow-hidden w-28">
      <div className="bg-forecast-below rounded-l" style={{ width: toW(below) }} title={`Below ${toW(below)}`} />
      <div className="bg-forecast-near"            style={{ width: toW(near)  }} title={`Near ${toW(near)}`} />
      <div className="bg-forecast-above rounded-r" style={{ width: toW(above) }} title={`Above ${toW(above)}`} />
    </div>
  );
}

// ── Tier pill ─────────────────────────────────────────────────────────────────
function TierPill({ tier }: { tier: string }) {
  if (tier === "full") {
    return (
      <span className="text-xs px-1.5 py-0.5 rounded bg-teal-900/40 border border-teal-600/30 text-teal-300 font-medium">
        Full
      </span>
    );
  }
  if (tier === "experimental") {
    return (
      <span className="text-xs px-1.5 py-0.5 rounded bg-amber-900/40 border border-amber-600/30 text-amber-300 font-medium">
        Exp.
      </span>
    );
  }
  return (
    <span className="text-xs px-1.5 py-0.5 rounded bg-red-900/40 border border-red-600/30 text-red-300 font-medium">
      Supp.
    </span>
  );
}

// ── Zone row ──────────────────────────────────────────────────────────────────
function ZoneRow({ zone }: { zone: ZoneForecastResult }) {
  const labelClass = predictionTextClass(zone.prediction);
  const isSuppressed = zone.no_skill;

  return (
    <tr className="border-b border-background-border last:border-0 hover:bg-background-elevated/40 transition-colors">
      {/* Zone name */}
      <td className="py-2.5 pr-3 text-sm text-text-secondary font-medium">
        {zone.zone_display ?? zone.zone}
        {zone.source === "region_fallback" && (
          <span className="ml-1.5 text-xs text-amber-400/70 font-normal">↩ fallback</span>
        )}
      </td>

      {/* Prediction */}
      <td className={`py-2.5 pr-3 text-sm font-semibold ${isSuppressed ? "text-text-faint" : labelClass}`}>
        {isSuppressed ? "—" : zone.prediction}
      </td>

      {/* Probability bars */}
      <td className="py-2.5 pr-3">
        {isSuppressed ? (
          <span className="text-xs text-text-faint italic">Suppressed</span>
        ) : (
          <MiniProbBars below={zone.prob_below} near={zone.prob_near} above={zone.prob_above} />
        )}
      </td>

      {/* Tier + RO-HSS */}
      <td className="py-2.5 text-right">
        <div className="flex items-center justify-end gap-2">
          <span className="text-xs font-mono text-text-faint">{formatHss(zone.ro_hss)}</span>
          <TierPill tier={zone.release_tier} />
        </div>
      </td>
    </tr>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
function SkeletonRow() {
  return (
    <tr className="border-b border-background-border">
      <td className="py-2.5 pr-3"><div className="h-3 w-28 rounded bg-background-border animate-pulse" /></td>
      <td className="py-2.5 pr-3"><div className="h-3 w-20 rounded bg-background-border animate-pulse" /></td>
      <td className="py-2.5 pr-3"><div className="h-2 w-28 rounded bg-background-border animate-pulse" /></td>
      <td className="py-2.5 text-right"><div className="h-3 w-16 rounded bg-background-border animate-pulse ml-auto" /></td>
    </tr>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export function RegionDrillDown({ regionKey, regionDisplay, season, onClose }: Props) {
  const { data: zones, isLoading, error } = useRegionZoneForecasts(regionKey, season, true);

  return (
    <div className="rounded-xl border border-background-border bg-background-surface overflow-hidden mt-4">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-background-border bg-background-elevated">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-text-primary">
            {regionDisplay} — Zone Breakdown
          </h2>
          <span className="text-xs text-text-faint px-2 py-0.5 rounded bg-background-border/60">
            {season}
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-text-muted hover:text-text-primary transition-colors p-1 rounded"
          aria-label="Close drill-down"
        >
          <X size={16} />
        </button>
      </div>

      {/* Legend row */}
      <div className="flex items-center gap-4 px-5 py-2 bg-background-elevated/50 border-b border-background-border text-xs text-text-faint">
        <ZoneSourceBadge source="zone" />
        <span>= zone-specific model</span>
        <ZoneSourceBadge source="region_fallback" />
        <span>= region model used</span>
      </div>

      {/* Table */}
      <div className="px-5 py-3 overflow-x-auto">
        {error ? (
          <p className="text-sm text-text-muted py-4 text-center">
            Failed to load zone forecasts.
          </p>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr className="text-left text-xs text-text-muted uppercase tracking-wide">
                <th className="pb-2 pr-3 font-medium">Zone</th>
                <th className="pb-2 pr-3 font-medium">Outlook</th>
                <th className="pb-2 pr-3 font-medium">Probability</th>
                <th className="pb-2 text-right font-medium">RO-HSS / Tier</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <>
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                </>
              ) : !zones || zones.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-6 text-center text-sm text-text-muted">
                    No zone data available for {regionDisplay}.
                  </td>
                </tr>
              ) : (
                zones.map((z) => (
                  <ZoneRow key={z.zone_key ?? z.zone} zone={z} />
                ))
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Probability legend */}
      <div className="flex items-center gap-3 px-5 py-2 border-t border-background-border bg-background-elevated/30 text-xs text-text-faint">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded bg-forecast-below" /> Below
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded bg-forecast-near" /> Near
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded bg-forecast-above" /> Above
        </span>
        <span className="ml-auto">RO-HSS = rolling-origin Heidke Skill Score</span>
      </div>
    </div>
  );
}
