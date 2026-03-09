// ── Formatting utilities ──────────────────────────────────────────

/** Format a 0–1 probability as a percentage string. e.g. 0.456 → "46%" */
export function formatPct(value: number, decimals = 0): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

/** Format a signed HSS value. e.g. 0.063 → "+0.063" | -0.111 → "−0.111" */
export function formatHss(value: number): string {
  const sign = value >= 0 ? "+" : "−";
  return `${sign}${Math.abs(value).toFixed(3)}`;
}

/** Format rainfall in mm. e.g. 287.3 → "287 mm" */
export function formatMm(value: number): string {
  return `${Math.round(value)} mm`;
}

/** Format an anomaly percentage with sign. e.g. 15.2 → "+15.2%" | -23.4 → "−23.4%" */
export function formatAnomalyPct(value: number): string {
  const sign = value >= 0 ? "+" : "−";
  return `${sign}${Math.abs(value).toFixed(1)}%`;
}

/** Format a z-score. e.g. +0.98 → "+0.98σ" */
export function formatZScore(value: number): string {
  const sign = value >= 0 ? "+" : "−";
  return `${sign}${Math.abs(value).toFixed(2)}σ`;
}

/** Format currency. e.g. 3450 → "3,450 ETB"
 *  Uses "en-US" locale (universally supported) for consistent comma separators.
 *  Rounds to the nearest integer — grain prices in Ethiopia are quoted in whole ETB. */
export function formatEtb(value: number): string {
  return `${Math.round(value).toLocaleString("en-US")} ETB`;
}

/** Format a trend percentage. e.g. 8.5 → "+8.5% vs last month" */
export function formatTrend(value: number | null): string {
  if (value === null) return "No comparison data";
  const sign = value >= 0 ? "+" : "−";
  return `${sign}${Math.abs(value).toFixed(1)}% vs last month`;
}

/** Return a trend colour class based on price change direction/magnitude */
export function trendColor(value: number | null): string {
  if (value === null) return "text-text-faint";
  if (value > 10) return "text-forecast-below";
  if (value > 3) return "text-forecast-near";
  if (value < -3) return "text-forecast-above";
  return "text-text-muted";
}
