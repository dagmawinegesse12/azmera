"use client";

import { useEffect, useState } from "react";
import { PredictionLabel } from "@/types/forecast";

interface ProbabilityBarsProps {
  probBelow: number;
  probNear: number;
  probAbove: number;
  prediction: PredictionLabel;
}

interface BarConfig {
  key: PredictionLabel;
  label: string;
  prob: number;
  color: string;
}

const CLIMO_BASELINE_PCT = 33;

export function ProbabilityBars({
  probBelow,
  probNear,
  probAbove,
  prediction,
}: ProbabilityBarsProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const bars: BarConfig[] = [
    { key: "Above Normal", label: "Above Normal", prob: probAbove, color: "#27ae60" },
    { key: "Near Normal",  label: "Near Normal",  prob: probNear,  color: "#d4a017" },
    { key: "Below Normal", label: "Below Normal", prob: probBelow, color: "#e74c3c" },
  ];

  return (
    <div className="flex flex-col gap-3">
      {bars.map((bar) => {
        const isDominant = bar.key === prediction;
        const displayPct = mounted ? bar.prob : 0;

        return (
          <div key={bar.key} className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <span
                className={`text-sm ${
                  isDominant
                    ? "font-semibold text-text-primary"
                    : "font-normal text-text-secondary"
                }`}
              >
                {bar.label}
              </span>
              <span
                className={`text-sm font-mono ${
                  isDominant ? "font-bold text-text-primary" : "text-text-muted"
                }`}
              >
                {Math.round(bar.prob * 100)}%
              </span>
            </div>

            {/* Bar track */}
            <div
              className={`relative w-full rounded-full overflow-hidden bg-background-elevated ${
                isDominant ? "h-4" : "h-3"
              }`}
            >
              {/* Filled portion */}
              <div
                className="h-full rounded-full transition-all duration-700 ease-out"
                style={{
                  width: `${displayPct * 100}%`,
                  backgroundColor: bar.color,
                  opacity: isDominant ? 1 : 0.65,
                }}
              />

              {/* Climatological baseline dashed line at 33% */}
              <div
                className="absolute top-0 bottom-0 w-px border-l border-dashed border-text-faint/50 z-10"
                style={{ left: `${CLIMO_BASELINE_PCT}%` }}
                title="Climatological baseline (33%)"
              />
            </div>
          </div>
        );
      })}

      <p className="text-xs text-text-faint mt-1">
        Dashed line = climatological baseline (33% each class)
      </p>
    </div>
  );
}
