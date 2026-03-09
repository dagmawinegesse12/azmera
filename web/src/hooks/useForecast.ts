// ── Forecast query hooks ──────────────────────────────────────────
import { useQuery } from "@tanstack/react-query";
import { forecastApi } from "@/api/forecast";
import { useSelectionStore } from "@/store/selectionStore";
import type { SeasonKey, LanguageKey } from "@/types/forecast";

// ── Query keys ────────────────────────────────────────────────────
export const forecastKeys = {
  all:          ["forecast"] as const,
  region:       (region: string, season: SeasonKey, lang: LanguageKey) =>
                  [...forecastKeys.all, "region", region, season, lang] as const,
  zone:         (zone: string, region: string, season: SeasonKey, lang: LanguageKey) =>
                  [...forecastKeys.all, "zone", zone, region, season, lang] as const,
  allRegions:   (season: SeasonKey) =>
                  [...forecastKeys.all, "all-regions", season] as const,
  regionZones:  (region: string, season: SeasonKey) =>
                  [...forecastKeys.all, "region-zones", region, season] as const,
  zones:        (region: string) =>
                  ["zones", region] as const,
  chirps:       (region: string, season: SeasonKey) =>
                  ["chirps", region, season] as const,
  prices:       (region: string) =>
                  ["prices", region] as const,
  signals:      ["signals"] as const,
};

// ── Region forecast (main forecast panel) ─────────────────────────
export function useRegionForecast() {
  const { regionKey, seasonKey, language, forecastRequested } = useSelectionStore();

  return useQuery({
    queryKey: forecastKeys.region(regionKey, seasonKey, language),
    queryFn:  () => forecastApi.getRegionForecast({
      region: regionKey,
      season: seasonKey,
      lang:   language,
    }),
    enabled:    forecastRequested && !!regionKey && !!seasonKey,
    staleTime:  1000 * 60 * 60,      // 1 hour — matches Streamlit TTL
    gcTime:     1000 * 60 * 60 * 2,  // 2 hours in cache
    retry:      2,
  });
}

// ── Zone forecast (reads zone from store — no params needed) ──────
// Gated on forecastRequested AND zoneKey being non-null.
export function useZoneForecast() {
  const { regionKey, seasonKey, language, forecastRequested, zoneKey, zoneDisplay } =
    useSelectionStore();

  return useQuery({
    queryKey: forecastKeys.zone(zoneKey ?? "", regionKey, seasonKey, language),
    queryFn:  () =>
      forecastApi.getZoneForecast({
        zone:         zoneKey!,
        zone_display: zoneDisplay ?? zoneKey!,
        region:       regionKey,
        season:       seasonKey,
        lang:         language,
      }),
    enabled:    forecastRequested && !!zoneKey,
    staleTime:  1000 * 60 * 60,
    gcTime:     1000 * 60 * 60 * 2,
    retry:      2,
  });
}

// ── All-region forecasts (for map) ───────────────────────────────
export function useAllForecasts(season: SeasonKey) {
  return useQuery({
    queryKey: forecastKeys.allRegions(season),
    queryFn:  () => forecastApi.getAllForecasts(season),
    staleTime: 1000 * 60 * 60,
    gcTime:    1000 * 60 * 60 * 2,
  });
}

// ── Region zone forecasts (all zones for a region, map drill-down) ─
export function useRegionZoneForecasts(region: string, season: SeasonKey, enabled: boolean) {
  return useQuery({
    queryKey: forecastKeys.regionZones(region, season),
    queryFn:  () => forecastApi.getRegionZoneForecasts(region, season),
    enabled:  enabled && !!region,
    staleTime: 1000 * 60 * 60,
    gcTime:    1000 * 60 * 60 * 2,
  });
}

// ── Zone list (lightweight, no forecast data) ─────────────────────
// Used by ZoneSelector to populate the zone dropdown.
export function useRegionZones(region: string | null) {
  return useQuery({
    queryKey: forecastKeys.zones(region ?? ""),
    queryFn:  () => forecastApi.getZones(region!),
    enabled:  !!region,
    staleTime: 1000 * 60 * 60 * 24, // 24 h — zone list is static
    gcTime:    1000 * 60 * 60 * 48,
    retry:     1,
  });
}

// ── CHIRPS anomaly ────────────────────────────────────────────────
export function useChirpsAnomaly() {
  const { regionKey, seasonKey, forecastRequested } = useSelectionStore();

  return useQuery({
    queryKey: forecastKeys.chirps(regionKey, seasonKey),
    queryFn:  () => forecastApi.getChirpsAnomaly({ region: regionKey, season: seasonKey }),
    enabled:    forecastRequested,
    staleTime:  1000 * 60 * 60,
    gcTime:     1000 * 60 * 60 * 4,
  });
}

// ── Market prices ─────────────────────────────────────────────────
export function useMarketPrices() {
  const { regionKey, forecastRequested } = useSelectionStore();

  return useQuery({
    queryKey: forecastKeys.prices(regionKey),
    queryFn:  () => forecastApi.getPrices(regionKey),
    enabled:    forecastRequested,
    staleTime:  1000 * 60 * 60,
    gcTime:     1000 * 60 * 60 * 4,
  });
}

// ── Ocean signals ─────────────────────────────────────────────────
export function useSignals() {
  return useQuery({
    queryKey: forecastKeys.signals,
    queryFn:  forecastApi.getSignals,
    staleTime: 1000 * 60 * 60,
    gcTime:    1000 * 60 * 60 * 2,
    // Signals are always fetched on dashboard load (no forecastRequested gate)
  });
}
