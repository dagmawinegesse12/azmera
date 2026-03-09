"use client";

import { ForecastResult, LanguageKey } from "@/types/forecast";
import { formatPct, formatHss } from "@/utils/format";
import { predictionTextClass } from "@/utils/prediction";

interface ForecastVerdictCardProps {
  forecast: ForecastResult;
  language: LanguageKey;
}

function extractFirstBullet(advisory: string | null): string | null {
  if (!advisory) return null;
  const lines = advisory.split("\n");
  const bullet = lines.find((line) => line.trim().startsWith("•"));
  return bullet ? bullet.trim() : lines.find((l) => l.trim().length > 0) ?? null;
}

export function ForecastVerdictCard({ forecast, language }: ForecastVerdictCardProps) {
  const advisory =
    language === "am" ? forecast.advisory_am : forecast.advisory_en;
  const firstBullet = extractFirstBullet(advisory);

  const predictionClass = predictionTextClass(forecast.prediction);

  return (
    <div className="bg-background-elevated rounded-xl p-4 sm:p-6 border border-background-border flex flex-col items-center text-center gap-4">
      {/* Season badge */}
      <span className="text-xs uppercase tracking-widest text-text-muted font-semibold">
        {forecast.region} · {forecast.season}
      </span>

      {/* Main prediction label */}
      <div className="flex flex-col items-center gap-1">
        <span className={`text-3xl sm:text-4xl font-bold leading-tight ${predictionClass}`}>
          {forecast.prediction}
        </span>
        <span className="text-sm text-text-secondary">
          Confidence:{" "}
          <span className="font-semibold text-text-primary">
            {formatPct(forecast.confidence)}
          </span>
        </span>
      </div>

      {/* HSS context */}
      <p className="text-xs text-text-muted font-mono">
        Model skill (RO-HSS):{" "}
        <span className="text-text-secondary">{formatHss(forecast.ro_hss)}</span>
        {forecast.cv_hss != null && (
          <>
            {" · "}
            CV-HSS:{" "}
            <span className="text-text-secondary">{formatHss(forecast.cv_hss)}</span>
          </>
        )}
      </p>

      {/* First advisory bullet */}
      {firstBullet && (
        <p className="text-sm text-text-secondary leading-relaxed max-w-sm border-t border-background-border pt-4 w-full text-left">
          {firstBullet}
        </p>
      )}
    </div>
  );
}
