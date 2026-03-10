"use client";

import { AlertTriangle, XCircle } from "lucide-react";
import { ReleaseTier } from "@/types/forecast";
import { formatHss } from "@/utils/format";
import { useLocale } from "@/hooks/useLocale";

interface TierStatusBannerProps {
  tier: ReleaseTier;
  roHss: number;
}

export function TierStatusBanner({ tier, roHss }: TierStatusBannerProps) {
  const t = useLocale();

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
          <span className="font-semibold">{t.tier.experimentalLabel}</span>
          {" — "}
          {t.tier.experimentalPre}{" "}
          <span className="font-mono">{formatHss(roHss)}</span>
          {t.tier.experimentalPost}
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
          <span className="font-semibold">{t.tier.suppressedLabel}</span>
          {" — "}
          {t.tier.suppressedPre}{" "}
          <span className="font-mono">{formatHss(roHss)}</span>
          {t.tier.suppressedPost}
        </p>
      </div>
    );
  }

  return null;
}
