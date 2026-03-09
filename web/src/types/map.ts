// ── Map types ─────────────────────────────────────────────────────
import type { PredictionLabel, ReleaseTier } from "./forecast";

export interface GeoRegionFeature {
  type: "Feature";
  properties: {
    NAME_1: string;           // GeoJSON region name (may differ from Azmera key)
    azmera_key: string;       // Normalised Azmera region key
    prediction: PredictionLabel | null;
    release_tier: ReleaseTier;
    ro_hss: number;
    no_skill: boolean;
  };
  geometry: GeoJSON.Geometry;
}

export interface MapViewState {
  mode: "overview" | "zone-drill";
  drillRegion: string | null;   // Azmera region key, e.g. "oromia"
}

export type MapPredictionColor = {
  above: string;
  near: string;
  below: string;
  suppressed: string;
  unknown: string;
};
