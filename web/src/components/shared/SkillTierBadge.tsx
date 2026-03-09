"use client";

import { COLORS } from "@/constants/colors";

type Tier = "full" | "experimental" | "suppressed";

interface SkillTierBadgeProps {
  tier: Tier;
  hss?: number;
  showHss?: boolean;
}

const TIER_CONFIG: Record<
  Tier,
  { label: string; color: string; borderColor: string }
> = {
  full: {
    label:       "Full Forecast",
    color:       COLORS.tier.full,
    borderColor: COLORS.tier.full,
  },
  experimental: {
    label:       "Experimental",
    color:       COLORS.tier.experimental,
    borderColor: COLORS.tier.experimental,
  },
  suppressed: {
    label:       "Suppressed",
    color:       COLORS.tier.suppressed,
    borderColor: COLORS.tier.suppressed,
  },
};

function formatHss(hss: number): string {
  const sign = hss >= 0 ? "+" : "";
  return `${sign}${hss.toFixed(2)}`;
}

export function SkillTierBadge({ tier, hss, showHss = false }: SkillTierBadgeProps) {
  const { label, color, borderColor } = TIER_CONFIG[tier];

  const displayLabel =
    showHss && hss !== undefined
      ? `${label} (HSS ${formatHss(hss)})`
      : label;

  return (
    <span
      className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium"
      style={{ color, borderColor }}
    >
      {displayLabel}
    </span>
  );
}
