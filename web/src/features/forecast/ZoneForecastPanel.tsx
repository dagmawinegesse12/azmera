"use client";

/**
 * ZoneForecastPanel — full zone-level forecast display.
 *
 * Mirrors ForecastPanel but:
 *  - Reads from useZoneForecast() (no params — reads store)
 *  - Shows ZoneSourceBadge above the tier banner
 *  - CHIRPS + market prices still show (regional context)
 *  - SuppressedPanel cvHss is optional (zone results lack it)
 *
 * Language is read from the global Zustand store (set by TopNav toggle).
 */

import { useZoneForecast } from "@/hooks/useForecast";
import { useSelectionStore } from "@/store/selectionStore";
import { useLocale } from "@/hooks/useLocale";
import { EmptyState } from "@/components/shared/EmptyState";
import { ZoneSourceBadge } from "./ZoneSourceBadge";
import { TierStatusBanner } from "./TierStatusBanner";
import { OceanSignalsStrip } from "./OceanSignalsStrip";
import { ForecastVerdictCard } from "./ForecastVerdictCard";
import { ProbabilityBars } from "./ProbabilityBars";
import { ChirpsAnomalyCard } from "./ChirpsAnomalyCard";
import { AdvisoryCard } from "./AdvisoryCard";
import { MarketPricesPanel } from "./MarketPricesPanel";
import { SuppressedPanel } from "./SuppressedPanel";

export function ZoneForecastPanel() {
  const store    = useSelectionStore();
  const language = useSelectionStore((s) => s.language);
  const t        = useLocale();

  const forecastRequested = store.forecastRequested ?? false;
  const { data, isLoading, error } = useZoneForecast();

  // ── Not yet requested ─────────────────────────────────────────────────────
  if (!forecastRequested) {
    return (
      <div className="flex flex-col items-center gap-6 py-12">
        <EmptyState title={t.forecast.selectZonePrompt} />
        <button
          onClick={() => store.requestForecast()}
          className="bg-accent-green text-white rounded-lg px-6 py-3 font-medium hover:opacity-90 transition-opacity"
        >
          {t.selector.generateButton}
        </button>
      </div>
    );
  }

  // ── Loading ────────────────────────────────────────────────────────────────
  if (isLoading) {
    return <EmptyState isLoading title={t.forecast.loadingZone} />;
  }

  // ── Error ──────────────────────────────────────────────────────────────────
  if (error || !data) {
    const message =
      error instanceof Error
        ? error.message
        : t.forecast.errorZoneGeneric;

    return (
      <div className="rounded-xl bg-red-950/30 border border-red-700/40 p-6 flex flex-col gap-2">
        <p className="text-sm font-semibold text-red-300">{t.forecast.errorZoneTitle}</p>
        <p className="text-sm text-text-muted">{message}</p>
        <button
          onClick={() => store.requestForecast()}
          className="self-start mt-2 text-xs text-red-300 underline hover:text-red-200"
        >
          {t.forecast.tryAgain}
        </button>
      </div>
    );
  }

  const source         = data.source ?? "region_fallback";
  const fallbackReason = data.fallback_reason ?? null;

  // ── Suppressed ─────────────────────────────────────────────────────────────
  if (data.no_skill) {
    return (
      <div className="flex flex-col gap-4">
        {/* Source badge */}
        <div className="flex items-center gap-2">
          <ZoneSourceBadge source={source} fallbackReason={fallbackReason} />
        </div>
        <TierStatusBanner tier={data.release_tier} roHss={data.ro_hss} />
        <SuppressedPanel
          regionName={data.zone_display ?? data.zone ?? data.region}
          season={data.season}
          roHss={data.ro_hss}
          cvHss={data.cv_hss ?? null}
        />
      </div>
    );
  }

  // ── Full / Experimental zone forecast ──────────────────────────────────────
  return (
    <div className="flex flex-col gap-5">
      {/* 0. Source badge — always visible */}
      <div className="flex items-center gap-2">
        <ZoneSourceBadge source={source} fallbackReason={fallbackReason} />
      </div>

      {/* 1. Tier banner */}
      <TierStatusBanner tier={data.release_tier} roHss={data.ro_hss} />

      {/* 2. Ocean signals strip */}
      <OceanSignalsStrip />

      {/* 3. Verdict + probability bars (2-col on lg) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ForecastVerdictCard forecast={data} language={language} />
        <div className="bg-background-elevated rounded-xl p-6 border border-background-border flex flex-col justify-center gap-2">
          <h3 className="text-xs uppercase tracking-widest font-semibold text-text-muted mb-2">
            {t.forecast.probabilityDistribution}
          </h3>
          <ProbabilityBars
            probBelow={data.prob_below}
            probNear={data.prob_near}
            probAbove={data.prob_above}
            prediction={data.prediction}
          />
        </div>
      </div>

      {/* 4. CHIRPS anomaly (regional context — zone-level CHIRPS not available) */}
      <ChirpsAnomalyCard />

      {/* 5. Advisory */}
      <AdvisoryCard
        advisoryEn={data.advisory_en}
        advisoryAm={data.advisory_am}
        language={language}
        releaseTier={data.release_tier}
        roHss={data.ro_hss}
      />

      {/* 6. Market prices (regional context — zone-level prices not available) */}
      <MarketPricesPanel scopeNote={t.forecast.zonePricesNote} />
    </div>
  );
}
