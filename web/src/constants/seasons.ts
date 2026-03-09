// ── Season definitions ────────────────────────────────────────────
import type { SeasonKey } from "@/types/forecast";

export interface SeasonConfig {
  key: SeasonKey;
  label: string;
  months: string;
  hasForecasts: boolean;
  description: string;
}

export const SEASONS: SeasonConfig[] = [
  {
    key:          "Kiremt",
    label:        "Kiremt",
    months:       "Jun – Sep",
    hasForecasts: true,
    description:  "Main rainy season. Primary growing season for most of Ethiopia.",
  },
  {
    key:          "Belg",
    label:        "Belg",
    months:       "Mar – May",
    hasForecasts: true,
    description:  "Short rains. Critical growing season in central & eastern highlands.",
  },
  {
    key:          "OND",
    label:        "OND",
    months:       "Oct – Dec",
    hasForecasts: false,
    description:  "Short rains in southern and eastern Ethiopia. Monitoring only — no validated forecast.",
  },
  {
    key:          "Bega",
    label:        "Bega",
    months:       "Jan – Feb",
    hasForecasts: false,
    description:  "Dry season. Monitoring only — no validated forecast.",
  },
];

export const FORECAST_SEASONS: SeasonConfig[] = SEASONS.filter((s) => s.hasForecasts);

export const SEASON_MAP: Record<SeasonKey, SeasonConfig> = Object.fromEntries(
  SEASONS.map((s) => [s.key, s])
) as Record<SeasonKey, SeasonConfig>;
