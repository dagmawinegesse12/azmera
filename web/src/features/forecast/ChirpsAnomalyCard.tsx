"use client";

import { useChirpsAnomaly } from "@/hooks/useForecast";
import { useSelectionStore } from "@/store/selectionStore";
import { formatAnomalyPct, formatMm } from "@/utils/format";
import { predictionTextClass } from "@/utils/prediction";
import type { PredictionLabel } from "@/types/forecast";

function SkeletonAnomaly() {
  return (
    <div className="bg-background-elevated rounded-lg p-4 flex flex-col gap-3 animate-pulse">
      <div className="h-4 w-40 rounded bg-background-border" />
      <div className="h-7 w-24 rounded bg-background-border" />
      <div className="h-3 w-full rounded bg-background-border" />
      <div className="h-3 w-3/4 rounded bg-background-border" />
    </div>
  );
}

export function ChirpsAnomalyCard() {
  // Store uses "seasonKey", not "season"
  const { seasonKey: season } = useSelectionStore();
  const { data, isLoading, error } = useChirpsAnomaly();

  if (isLoading) {
    return <SkeletonAnomaly />;
  }

  if (error || !data) {
    return null;
  }

  const anomalyColor =
    data.anomaly_pct >= 0 ? "text-forecast-above" : "text-forecast-below";
  const tercileClass = predictionTextClass(data.tercile as PredictionLabel | null);

  const zSign = data.z_score >= 0 ? "+" : "";

  return (
    <div className="bg-background-elevated rounded-lg p-4 flex flex-col gap-2.5">
      {/* Title */}
      <h3 className="text-xs font-semibold uppercase tracking-widest text-text-muted">
        Observed Rainfall Anomaly ({season ?? data.season})
      </h3>

      {/* Anomaly percentage — large */}
      <div className="flex items-baseline gap-2">
        <span className={`text-3xl font-bold font-mono ${anomalyColor}`}>
          {formatAnomalyPct(data.anomaly_pct)}
        </span>
        {data.anomaly_mm != null && (
          <span className="text-sm text-text-muted">
            ({formatMm(data.anomaly_mm)})
          </span>
        )}
      </div>

      {/* Tercile + Z-score row */}
      <div className="flex items-center gap-3 text-sm">
        <span className={`font-semibold ${tercileClass}`}>
          {data.tercile}
        </span>
        <span className="text-text-faint">·</span>
        <span className="text-text-muted font-mono text-xs">
          Z: {zSign}{data.z_score.toFixed(1)}σ
        </span>
      </div>

      {/* Method note — explains why tercile and Z-score may appear to disagree */}
      <p className="text-xs text-text-faint mt-0.5 leading-snug">
        Status uses ±15% vs 1991–2020 baseline · Z-score is σ from climatological mean
      </p>
    </div>
  );
}
