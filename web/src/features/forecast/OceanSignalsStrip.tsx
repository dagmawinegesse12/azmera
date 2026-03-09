"use client";

import { useSignals } from "@/hooks/useForecast";
import { SignalPill } from "./SignalPill";
import { SignalValue } from "@/types/forecast";

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

function SkeletonPill() {
  return (
    <div className="bg-background-elevated animate-pulse rounded-full h-8 w-24 shrink-0" />
  );
}

export function OceanSignalsStrip() {
  const { data, isLoading, error } = useSignals();

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-2 px-0.5">
        <span className="text-xs font-semibold uppercase tracking-widest text-text-muted">
          Ocean Signals
        </span>
        {data?.fetched_at && (
          <span className="text-xs text-text-faint">
            Updated: {formatDate(data.fetched_at)}
          </span>
        )}
      </div>

      {error ? (
        <p className="text-sm text-text-muted py-2">Signal data unavailable</p>
      ) : (
        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
          {isLoading || !data ? (
            <>
              <SkeletonPill />
              <SkeletonPill />
              <SkeletonPill />
              <SkeletonPill />
              <SkeletonPill />
            </>
          ) : (
            <>
              <SignalPill label="ENSO" signal={data.enso} />
              <SignalPill label="IOD" signal={data.iod} />
              <SignalPill label="PDO" signal={data.pdo} />
              <SignalPill label="ATL" signal={data.atl} />
              {data.amm_jan && (
                <SignalPill
                  label="AMM"
                  signal={
                    {
                      value: data.amm_jan.value,
                      phase:
                        data.amm_jan.value > 0.5
                          ? "Positive"
                          : data.amm_jan.value < -0.5
                          ? "Negative"
                          : "Neutral",
                      label: "AMM",
                      description: "Atlantic Meridional Mode (Jan)",
                    } satisfies SignalValue
                  }
                />
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
