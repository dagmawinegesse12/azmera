"use client";

import { AlertTriangle, XCircle } from "lucide-react";
import { ReleaseTier } from "@/types/forecast";
import { formatHss } from "@/utils/format";

interface TierStatusBannerProps {
  tier: ReleaseTier;
  roHss: number;
}

export function TierStatusBanner({ tier, roHss }: TierStatusBannerProps) {
  if (tier === "full") {
    return null;
  }

  if (tier === "experimental") {
    return (
      <div className="w-full rounded-lg p-4 flex items-start gap-3 bg-amber-950/40 border border-amber-700/50">
        <AlertTriangle
          className="shrink-0 mt-0.5 text-amber-400"
          size={18}
          aria-hidden="true"
        />
        <p className="text-sm text-amber-200 leading-relaxed">
          <span className="font-semibold">Experimental Forecast</span> —
          Prospective skill score (RO-HSS:{" "}
          <span className="font-mono">{formatHss(roHss)}</span>) is positive but
          below the validated threshold (≥ 0.10). Use with caution.
        </p>
      </div>
    );
  }

  if (tier === "suppressed") {
    return (
      <div className="w-full rounded-lg p-4 flex items-start gap-3 bg-red-950/40 border border-red-700/50">
        <XCircle
          className="shrink-0 mt-0.5 text-red-400"
          size={18}
          aria-hidden="true"
        />
        <p className="text-sm text-red-200 leading-relaxed">
          <span className="font-semibold">No Validated Forecast</span> — This
          region-season has no positive prospective skill (RO-HSS:{" "}
          <span className="font-mono">{formatHss(roHss)}</span>). Model output
          is withheld.
        </p>
      </div>
    );
  }

  return null;
}
