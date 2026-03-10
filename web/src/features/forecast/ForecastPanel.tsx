"use client";

/**
 * ForecastPanel — top-level forecast results container.
 *
 * Branches between:
 *  - ZoneForecastPanel (when store.zoneKey is set — zone mode)
 *  - RegionForecastPanel (when store.zoneKey is null — region mode)
 *
 * Language is read from the global Zustand store (set by TopNav toggle).
 * No per-panel language state — the global toggle drives advisory language.
 */

import { useRegionForecast } from "@/hooks/useForecast";
import { useSelectionStore } from "@/store/selectionStore";
import { useLocale } from "@/hooks/useLocale";
import { EmptyState } from "@/components/shared/EmptyState";
import { TierStatusBanner } from "./TierStatusBanner";
import { OceanSignalsStrip } from "./OceanSignalsStrip";
import { ForecastVerdictCard } from "./ForecastVerdictCard";
import { ProbabilityBars } from "./ProbabilityBars";
import { ChirpsAnomalyCard } from "./ChirpsAnomalyCard";
import { AdvisoryCard } from "./AdvisoryCard";
import { MarketPricesPanel } from "./MarketPricesPanel";
import { SuppressedPanel } from "./SuppressedPanel";
import { ZoneForecastPanel } from "./ZoneForecastPanel";

// ── Region-level forecast panel ────────────────────────────────────────────
function RegionForecastPanel() {
  const store    = useSelectionStore();
  const language = useSelectionStore((s) => s.language);
  const t        = useLocale();

  const forecastRequested = store.forecastRequested ?? false;
  const { data, isLoading, error } = useRegionForecast();

  if (!forecastRequested) {
    return (
      <div className="flex flex-col items-center gap-6 py-12">
        <EmptyState title={t.forecast.selectPrompt} />
        <button
          onClick={() => store.requestForecast()}
          className="bg-accent-green text-white rounded-lg px-6 py-3 font-medium hover:opacity-90 transition-opacity"
        >
          {t.selector.generateButton}
        </button>
      </div>
    );
  }

  if (isLoading) {
    return <EmptyState isLoading title={t.forecast.loading} />;
  }

  if (error || !data) {
    const message =
      error instanceof Error
        ? error.message
        : t.forecast.errorGeneric;

    return (
      <div className="rounded-xl bg-red-950/30 border border-red-700/40 p-6 flex flex-col gap-2">
        <p className="text-sm font-semibold text-red-300">{t.forecast.errorTitle}</p>
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

  if (data.no_skill) {
    return (
      <div className="flex flex-col gap-4">
        <TierStatusBanner tier={data.release_tier} roHss={data.ro_hss} />
        <SuppressedPanel
          regionName={data.region}
          season={data.season}
          roHss={data.ro_hss}
          cvHss={data.cv_hss ?? null}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <TierStatusBanner tier={data.release_tier} roHss={data.ro_hss} />
      <OceanSignalsStrip />

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

      <ChirpsAnomalyCard />
      <AdvisoryCard
        advisoryEn={data.advisory_en}
        advisoryAm={data.advisory_am}
        language={language}
        releaseTier={data.release_tier}
        roHss={data.ro_hss}
      />
      <MarketPricesPanel />
    </div>
  );
}

// ── Public export ──────────────────────────────────────────────────────────
// Routes to ZoneForecastPanel or RegionForecastPanel based on store state.
// Both are full components with their own hooks — no conditional hook calls.
export function ForecastPanel() {
  const zoneKey = useSelectionStore((s) => s.zoneKey);
  return zoneKey ? <ZoneForecastPanel /> : <RegionForecastPanel />;
}
