// ── Validation types ──────────────────────────────────────────────
// Field names match 1:1 with api/server.py validation endpoints.
// Previous nested shapes (metrics/by_region/drought_years) did not match backend.

// ── Validation summary ────────────────────────────────────────────
// Matches GET /validation/summary → flat object per season.
// Components use: aggregate_hss, loocv_hss, n_full, n_experimental, n_suppressed

export interface ValidationSummary {
  season: string;
  aggregate_hss: number;   // rolling-origin HSS — prospective / honest metric
  loocv_hss: number;       // LOOCV HSS — reference (optimistic)
  n_regions: number;
  n_full: number;
  n_experimental: number;
  n_suppressed: number;
  n_test_years: number;
}

// ── Release matrix ────────────────────────────────────────────────
// Matches GET /validation/release-matrix → flat array of ReleaseMatrixRow.
// Components iterate data directly: [...data].sort(...), row.region_key, etc.

export interface ReleaseMatrixRow {
  region_key: string;        // e.g. "amhara"
  region_display: string;    // e.g. "Amhara"
  ro_hss: number;            // rolling-origin HSS
  cv_hss: number | null;     // LOOCV HSS (null if no CSV rows for this region)
  tier: "full" | "experimental" | "suppressed";
  n_test_years: number;
}

// Backend returns a flat array — NOT {regions: [...], aggregates: {...}}
export type ReleaseMatrix = ReleaseMatrixRow[];

// ── Timeline ──────────────────────────────────────────────────────
// Matches GET /validation/timeline → flat array of year-by-year rows.

export interface TimelineRow {
  year: number;
  actual: string;      // "Below Normal" | "Near Normal" | "Above Normal"
  predicted: string;
  correct: boolean;
  prob_below: number;
  prob_near: number;
  prob_above: number;
}

export type TimelineData = TimelineRow[];

// ── Reliability diagram ───────────────────────────────────────────
// Matches GET /validation/reliability → flat array of binned scatter points.
// Components access: data.length, data.map(d => d.n), pt.forecast_prob, pt.observed_freq, pt.n

export interface ReliabilityPoint {
  class: number;          // 0=Below Normal, 1=Near Normal, 2=Above Normal
  forecast_prob: number;  // bin centre, 0–1
  observed_freq: number;  // fraction actually observed in this bin, 0–1
  n: number;              // number of forecasts in bin
}

// Backend returns a flat array — NOT {bins: [...]}
export type ReliabilityData = ReliabilityPoint[];

// ── Limitation ────────────────────────────────────────────────────

export type LimitationSeverity = "fundamental" | "significant" | "moderate";

export interface Limitation {
  title: string;
  severity: LimitationSeverity;
  detail: string;
  status: string;
}
