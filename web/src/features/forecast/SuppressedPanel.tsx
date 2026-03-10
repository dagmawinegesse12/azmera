"use client";

import { XCircle } from "lucide-react";
import { SeasonKey } from "@/types/forecast";
import { formatHss } from "@/utils/format";
import { useLocale } from "@/hooks/useLocale";

interface SuppressedPanelProps {
  regionName: string;
  season: SeasonKey;
  roHss: number;
  cvHss?: number | null;
}

export function SuppressedPanel({
  regionName,
  season,
  roHss,
  cvHss,
}: SuppressedPanelProps) {
  const t = useLocale();

  return (
    <div className="bg-background-surface rounded-xl p-8 flex flex-col items-center text-center gap-5">
      {/* Icon */}
      <XCircle
        size={56}
        className="text-red-500/70"
        aria-hidden="true"
        strokeWidth={1.5}
      />

      {/* Heading */}
      <div className="flex flex-col gap-1">
        <h2 className="text-xl font-bold text-text-primary">
          {t.suppressed.heading}
        </h2>
        <p className="text-sm text-text-muted">
          {regionName} · {season}
        </p>
      </div>

      {/* Explanation */}
      <p className="text-sm text-text-secondary leading-relaxed max-w-md">
        {t.suppressed.explanationPre}{" "}
        <span className="font-mono text-red-400">{formatHss(roHss)}</span>
        {t.suppressed.explanationPost}
      </p>

      {/* CV-HSS note — only when available */}
      {cvHss != null && (
        <div className="mt-2 flex flex-col items-center gap-0.5 border-t border-background-border pt-4 w-full">
          <p className="text-xs text-text-muted">
            {t.suppressed.cvHssLabel}:{" "}
            <span className="font-mono text-text-secondary">
              {formatHss(cvHss)}
            </span>
          </p>
          <p className="text-xs text-text-faint italic">
            {t.suppressed.cvHssNote}
          </p>
        </div>
      )}
    </div>
  );
}
