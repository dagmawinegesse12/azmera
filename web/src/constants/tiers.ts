// ── Release tier definitions ──────────────────────────────────────
// These thresholds must stay in sync with forecaster.py.

import type { ReleaseTier } from "@/types/forecast";

export const RO_FULL_THRESHOLD        = 0.10;
export const RO_SUPPRESS_THRESHOLD    = 0.00;

// Per-region rolling-origin HSS values (hardcoded from Phase D/F results).
// These mirror KIREMT_RO_HSS and BELG_RO_HSS in src/forecaster.py.
// If forecaster.py is updated, this file must be updated to match.
export const KIREMT_RO_HSS: Record<string, number> = {
  addis_ababa:       -0.049,
  afar:              +0.071,
  amhara:            +0.044,
  benishangul_gumz:  +0.471,
  dire_dawa:         +0.024,
  gambela:           +0.012,
  harari:            +0.102,
  oromia:            -0.111,
  sidama:            -0.130,
  snnpr:             +0.077,
  somali:            +0.206,
  south_west:        +0.025,
  tigray:            +0.106,
};

export const BELG_RO_HSS: Record<string, number> = {
  addis_ababa:       +0.111,
  afar:              +0.046,
  amhara:            +0.199,
  benishangul_gumz:  +0.056,
  dire_dawa:         +0.096,
  gambela:           +0.147,
  harari:            +0.096,
  oromia:            -0.084,
  sidama:            -0.025,
  snnpr:             -0.101,
  somali:            +0.100,
  south_west:        +0.160,
  tigray:            +0.032,
};

export function getReleaseTier(regionKey: string, season: "Kiremt" | "Belg"): ReleaseTier {
  const lookup = season === "Kiremt" ? KIREMT_RO_HSS : BELG_RO_HSS;
  const hss = lookup[regionKey];
  if (hss === undefined) return "experimental";
  if (hss >= RO_FULL_THRESHOLD) return "full";
  if (hss > RO_SUPPRESS_THRESHOLD) return "experimental";
  return "suppressed";
}

export function getRoHss(regionKey: string, season: "Kiremt" | "Belg"): number | undefined {
  return season === "Kiremt" ? KIREMT_RO_HSS[regionKey] : BELG_RO_HSS[regionKey];
}

// ── UI representation of each tier ───────────────────────────────

export interface TierConfig {
  label: string;
  shortLabel: string;
  icon: string;
  color: string;       // Tailwind text color class
  bgColor: string;     // Tailwind bg color class
  borderColor: string; // Tailwind border color class
  hexColor: string;    // Raw hex for non-Tailwind usage (e.g. chart markers)
}

export const TIER_CONFIG: Record<ReleaseTier, TierConfig> = {
  full: {
    label:       "Full Forecast",
    shortLabel:  "Full",
    icon:        "✅",
    color:       "text-tier-full",
    bgColor:     "bg-tier-full-bg",
    borderColor: "border-tier-full",
    hexColor:    "#27ae60",
  },
  experimental: {
    label:       "Experimental",
    shortLabel:  "Exp.",
    icon:        "⚠️",
    color:       "text-tier-experimental",
    bgColor:     "bg-tier-experimental-bg",
    borderColor: "border-tier-experimental",
    hexColor:    "#d4a017",
  },
  suppressed: {
    label:       "Suppressed — No Forecast",
    shortLabel:  "Suppressed",
    icon:        "❌",
    color:       "text-tier-suppressed",
    bgColor:     "bg-tier-suppressed-bg",
    borderColor: "border-tier-suppressed",
    hexColor:    "#e74c3c",
  },
};

// Aggregate rolling-origin HSS
export const KIREMT_AGGREGATE_RO_HSS = +0.063;
export const BELG_AGGREGATE_RO_HSS   = +0.071;
export const WMO_SKILLFUL_THRESHOLD   = 0.30;
