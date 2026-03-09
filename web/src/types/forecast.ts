// ── Forecast types ────────────────────────────────────────────────
// Field names match 1:1 with api/server.py FastAPI responses.
// Previous version had incorrect shapes; this is authoritative.

export type SeasonKey = "Kiremt" | "Belg" | "OND" | "Bega";
export type PredictionLabel = "Below Normal" | "Near Normal" | "Above Normal";
export type AnomalyStatus = PredictionLabel;   // alias used by prediction utils
export type ReleaseTier = "full" | "experimental" | "suppressed";
export type LanguageKey = "en" | "am";

// ── Region metadata ───────────────────────────────────────────────

export interface Region {
  key: string;           // e.g. "amhara"
  display: string;       // e.g. "Amhara"
  zones?: Zone[];        // optional — /regions does not return zones yet
}

export interface Zone {
  key: string;           // e.g. "north_gondar"
  display: string;       // e.g. "North Gondar"
}

// ── Ocean signals ─────────────────────────────────────────────────
// Matches api/server.py GET /signals per-signal object.
// Backend returns {value, phase, label, description} — lag fields removed.

export interface SignalValue {
  value: number;
  phase: string;         // e.g. "El Niño", "Neutral", "Positive IOD"
  label?: string;        // e.g. "ENSO" — present in backend response
  description?: string;  // e.g. "El Niño–Southern Oscillation (Niño 3.4)"
}

export interface OceanSignals {
  enso: SignalValue;
  iod: SignalValue;
  pdo: SignalValue;
  atl: SignalValue;
  amm_jan: { value: number } | null;   // null when unavailable
  fetched_at: string;                  // ISO timestamp
}

// ── Forecast result ───────────────────────────────────────────────
// Matches api/server.py GET /forecast response.

export interface ForecastResult {
  region: string;
  season: SeasonKey;
  prediction: PredictionLabel;
  prob_below: number;       // 0–1
  prob_near: number;
  prob_above: number;
  confidence: number;       // max(probs), 0–1
  cv_hss?: number;          // LOOCV HSS (reference only); absent in zone results
  cv_accuracy?: number;     // extra field from backend, optional
  release_tier: ReleaseTier;
  ro_hss: number;           // rolling-origin HSS (basis for tier)
  no_skill: boolean;        // true when release_tier === 'suppressed'
  advisory_en: string | null;
  advisory_am: string | null;
  enso_current: number;
  enso_phase: string;
  source?: string;
}

// ── Zone info (from GET /zones) ───────────────────────────────────
// Lightweight zone list — no forecast data.

export interface ZoneInfo {
  zone_key: string;     // e.g. "north_gondar"
  zone_display: string; // e.g. "North Gondar"
}

// ── Zone forecast result ──────────────────────────────────────────
// Matches api/server.py GET /forecast/zone and GET /forecast/zones items.
// source="zone" → zone-specific model was used.
// source="region_fallback" → no zone model; region result substituted.

export interface ZoneForecastResult extends ForecastResult {
  zone: string;                            // zone display name (from backend)
  zone_key: string;                        // e.g. "north_gondar"
  zone_display: string;                    // e.g. "North Gondar"
  source: "zone" | "region_fallback";      // model source
  fallback_to_region?: boolean;            // true when source === "region_fallback"
  fallback_reason?: string;               // human-readable reason for fallback
}

// ── All-regions forecast (for map) ───────────────────────────────
// Matches api/server.py GET /forecast/all → flat array response.

export interface RegionForecastSummary {
  region_key: string;       // e.g. "oromia"  ← was "region", now matches backend
  region_display: string;   // e.g. "Oromia"
  prediction: PredictionLabel | null;
  release_tier: ReleaseTier;
  tier: ReleaseTier;        // alias for release_tier — added by backend for map compat
  ro_hss: number;
  no_skill: boolean;
  prob_below: number;
  prob_near: number;
  prob_above: number;
}

// Backend returns a flat array, NOT {season, forecasts: [...]}
export type AllForecastsResult = RegionForecastSummary[];

// ── CHIRPS observed anomaly ───────────────────────────────────────
// Matches api/server.py GET /chirps-anomaly normalised response.
// NOTE: rasterio must be installed for this to return data; otherwise null.

export interface ChirpsAnomaly {
  region: string;
  season: string;
  anomaly_pct: number;        // e.g. +15.2 or -23.4 (percent vs baseline)
  anomaly_mm: number | null;  // total mm anomaly (was "total_mm" in old type)
  tercile: string;            // "Above Normal" | "Near Normal" | "Below Normal"
  z_score: number;
  completed: boolean | null;
  label: string | null;
}

// ── Market prices ─────────────────────────────────────────────────
// Matches api/server.py GET /prices normalised response.
// Backend returns a flat array of CropPriceRow objects.

export interface CropPriceRow {
  commodity: string;              // e.g. "Teff (white)"  ← was "crop" in raw backend
  price_etb: number;              // ETB per quintal (100 kg)
  unit: string;                   // "per quintal (100kg)"
  date: string;                   // e.g. "Jan 2026"
  price_change_pct: number | null; // % change vs last month (null = no data)
  trend_label: string;            // "+8% vs last month" or "No comparison data"
  market_name: string;            // region/market label
  is_regional: boolean;
}

// useMarketPrices returns CropPriceRow[] (flat array)
export type MarketPrices = CropPriceRow[];

// ── API request params ────────────────────────────────────────────

export interface ForecastParams {
  region: string;
  season: SeasonKey;
  lang?: LanguageKey;
}

export interface ZoneForecastParams {
  zone: string;
  zone_display: string;
  region: string;
  season: SeasonKey;
  lang?: LanguageKey;
}

export interface ChirpsParams {
  region: string;
  season: SeasonKey;
}

export interface ZonesParams {
  region: string;
}
