// ── Validation API functions ──────────────────────────────────────
import { api } from "./client";
import type {
  ValidationSummary,
  TimelineData,
  ReliabilityData,
  ReleaseMatrix,
} from "@/types/validation";
import type { SeasonKey } from "@/types/forecast";

export const validationApi = {
  /**
   * Aggregate validation summary (skill scores, tier counts) for one season.
   * Maps to Next.js route: GET /api/validation/summary?season=Kiremt
   */
  getSummary: (season: SeasonKey): Promise<ValidationSummary> =>
    api.get("/validation/summary", { season }),

  /**
   * Rolling-origin year-by-year timeline for a single region + season.
   * Maps to Next.js route: GET /api/validation/timeline?region=tigray&season=Kiremt
   */
  getTimeline: (region: string, season: SeasonKey): Promise<TimelineData> =>
    api.get("/validation/timeline", { region, season }),

  /**
   * Reliability diagram data (calibration) for a single region + season.
   * Maps to Next.js route: GET /api/validation/reliability?region=tigray&season=Kiremt
   */
  getReliability: (region: string, season: SeasonKey): Promise<ReliabilityData> =>
    api.get("/validation/reliability", { region, season }),

  /**
   * Full release matrix: per-region rolling-origin HSS + tier for one season.
   * Maps to Next.js route: GET /api/validation/release-matrix?season=Kiremt
   */
  getReleaseMatrix: (season: SeasonKey): Promise<ReleaseMatrix> =>
    api.get("/validation/release-matrix", { season }),
};
