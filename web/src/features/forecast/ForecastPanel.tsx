"use client";

/**
 * ForecastPanel — top-level forecast results container.
 *
 * Branches between:
 *  - ZoneForecastPanel (when store.zoneKey is set — zone mode)
 *  - RegionForecastPanel (when store.zoneKey is null — region mode)
 *
 * The split avoids conditional hook calls; each sub-panel owns its own
 * data hook so React rules of hooks are satisfied.
 */

import { useState } from "react";
import { useRegionForecast } from "@/hooks/useForecast";
import { useSelectionStore } from "@/store/selectionStore";
import { LanguageKey } from "@/types/forecast";
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
  const store = useSelectionStore();
  const [language, setLanguage] = useState<LanguageKey>("en");

  const forecastRequested = store.forecastRequested ?? false;
  const { data, isLoading, error } = useRegionForecast();

  if (!forecastRequested) {
    return (
      <div className="flex flex-col items-center gap-6 py-12">
        <EmptyState title="Select a region and season, then click Generate Forecast" />
        <button
          onClick={() => store.requestForecast()}
          className="bg-accent-green text-white rounded-lg px-6 py-3 font-medium hover:opacity-90 transition-opacity"
        >
          Generate Forecast
        </button>
      </div>
    );
  }

  if (isLoading) {
    return <EmptyState isLoading title="Fetching forecast…" />;
  }

  if (error || !data) {
    const message =
      error instanceof Error
        ? error.message
        : "An unexpected error occurred while fetching the forecast.";

    return (
      <div className="rounded-xl bg-red-950/30 border border-red-700/40 p-6 flex flex-col gap-2">
        <p className="text-sm font-semibold text-red-300">Failed to load forecast</p>
        <p className="text-sm text-text-muted">{message}</p>
        <button
          onClick={() => store.requestForecast()}
          className="self-start mt-2 text-xs text-red-300 underline hover:text-red-200"
        >
          Try again
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
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs uppercase tracking-widest font-semibold text-text-muted">
              Probability Distribution
            </h3>
            <div className="flex items-center rounded-md overflow-hidden border border-background-border text-xs font-medium">
              <button
                onClick={() => setLanguage("en")}
                className={`px-2.5 py-1 transition-colors ${
                  language === "en"
                    ? "bg-background-surface text-text-primary"
                    : "text-text-muted hover:text-text-secondary"
                }`}
                aria-pressed={language === "en"}
              >
                EN
              </button>
              <button
                onClick={() => setLanguage("am")}
                className={`px-2.5 py-1 transition-colors ${
                  language === "am"
                    ? "bg-background-surface text-text-primary"
                    : "text-text-muted hover:text-text-secondary"
                }`}
                aria-pressed={language === "am"}
              >
                አማ
              </button>
            </div>
          </div>
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
