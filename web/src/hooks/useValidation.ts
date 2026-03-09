// ── Validation query hooks ─────────────────────────────────────────
import { useQuery } from "@tanstack/react-query";
import { validationApi } from "@/api/validation";
import type { SeasonKey } from "@/types/forecast";

// ── Query keys ────────────────────────────────────────────────────
export const validationKeys = {
  all:           ["validation"] as const,
  summary:       (season: SeasonKey) =>
                   [...validationKeys.all, "summary", season] as const,
  timeline:      (region: string, season: SeasonKey) =>
                   [...validationKeys.all, "timeline", region, season] as const,
  reliability:   (region: string, season: SeasonKey) =>
                   [...validationKeys.all, "reliability", region, season] as const,
  releaseMatrix: (season: SeasonKey) =>
                   [...validationKeys.all, "release-matrix", season] as const,
};

// ── Aggregate validation summary ──────────────────────────────────
export function useValidationSummary(season: SeasonKey) {
  return useQuery({
    queryKey: validationKeys.summary(season),
    queryFn:  () => validationApi.getSummary(season),
    staleTime: 1000 * 60 * 60 * 24,  // 24h — static validation metrics don't change
    gcTime:    1000 * 60 * 60 * 48,
  });
}

// ── Per-region timeline (rolling-origin year-by-year) ─────────────
export function useValidationTimeline(region: string, season: SeasonKey) {
  return useQuery({
    queryKey: validationKeys.timeline(region, season),
    queryFn:  () => validationApi.getTimeline(region, season),
    enabled:  !!region && !!season,
    staleTime: 1000 * 60 * 60 * 24,
    gcTime:    1000 * 60 * 60 * 48,
  });
}

// ── Reliability diagram data ───────────────────────────────────────
export function useReliabilityData(region: string, season: SeasonKey) {
  return useQuery({
    queryKey: validationKeys.reliability(region, season),
    queryFn:  () => validationApi.getReliability(region, season),
    enabled:  !!region && !!season,
    staleTime: 1000 * 60 * 60 * 24,
    gcTime:    1000 * 60 * 60 * 48,
  });
}

// ── Full release matrix ────────────────────────────────────────────
export function useReleaseMatrix(season: SeasonKey) {
  return useQuery({
    queryKey: validationKeys.releaseMatrix(season),
    queryFn:  () => validationApi.getReleaseMatrix(season),
    staleTime: 1000 * 60 * 60 * 24,
    gcTime:    1000 * 60 * 60 * 48,
  });
}
