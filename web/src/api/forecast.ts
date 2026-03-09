// ── Forecast API functions ────────────────────────────────────────
import { api } from "./client";
import type {
  ForecastResult,
  ZoneForecastResult,
  ZoneInfo,
  AllForecastsResult,
  ChirpsAnomaly,
  MarketPrices,
  OceanSignals,
  ForecastParams,
  ZoneForecastParams,
  ChirpsParams,
  SeasonKey,
  LanguageKey,
  Region,
} from "@/types/forecast";

export const forecastApi = {
  /**
   * Generate a forecast for a single region+season.
   * Maps to Next.js route: GET /api/forecast?region=...&season=...&lang=...
   */
  getRegionForecast: ({ region, season, lang }: ForecastParams): Promise<ForecastResult> =>
    api.get("/forecast", { region, season, lang }),

  /**
   * Generate a forecast for a single zone+season.
   * Maps to Next.js route: GET /api/forecast/zone?zone=...&region=...&season=...&lang=...
   */
  getZoneForecast: ({ zone, zone_display, region, season, lang }: ZoneForecastParams): Promise<ZoneForecastResult> =>
    api.get("/forecast/zone", { zone, zone_display, region, season, lang }),

  /**
   * Quick-summary forecasts for ALL regions (for the risk map).
   * Does not include advisory text — only predictions + tiers.
   * Maps to Next.js route: GET /api/forecast/all?season=...
   */
  getAllForecasts: (season: SeasonKey): Promise<AllForecastsResult> =>
    api.get("/forecast/all", { season }),

  /**
   * All zone forecasts for a single region (for zone drill-down).
   * Maps to Next.js route: GET /api/forecast/zones?region=...&season=...
   */
  getRegionZoneForecasts: (region: string, season: SeasonKey): Promise<ZoneForecastResult[]> =>
    api.get("/forecast/zones", { region, season }),

  /**
   * Lightweight zone list for a region (no forecast data).
   * Maps to Next.js route: GET /api/zones?region=...
   */
  getZones: (region: string): Promise<ZoneInfo[]> =>
    api.get("/zones", { region }),

  /**
   * CHIRPS season-to-date observed rainfall vs 1991–2020 baseline.
   * Maps to Next.js route: GET /api/chirps-anomaly?region=...&season=...
   */
  getChirpsAnomaly: ({ region, season }: ChirpsParams): Promise<ChirpsAnomaly | null> =>
    api.get("/chirps-anomaly", { region, season }),

  /**
   * WFP/HDX market prices for key crops in a region.
   * Maps to Next.js route: GET /api/prices?region=...
   */
  getPrices: (region: string): Promise<MarketPrices> =>
    api.get("/prices", { region }),

  /**
   * Latest ocean index values (ENSO, IOD, PDO, ATL, AMM).
   * Maps to Next.js route: GET /api/signals
   */
  getSignals: (): Promise<OceanSignals> =>
    api.get("/signals"),

  /**
   * All region metadata (display names + zone lists).
   * Maps to Next.js route: GET /api/regions
   */
  getRegions: (): Promise<{ regions: Region[] }> =>
    api.get("/regions"),
};
