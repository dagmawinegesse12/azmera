// ── Global UI selection state ─────────────────────────────────────
// Uses Zustand for lightweight client state.
// Server/async state (forecast results, etc.) is in TanStack Query hooks.

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { SeasonKey, LanguageKey } from "@/types/forecast";

interface SelectionState {
  // Current selections
  regionKey: string;          // e.g. "amhara"
  seasonKey: SeasonKey;
  zoneKey: string | null;     // null = region-level forecast; e.g. "north_gondar"
  zoneDisplay: string | null; // display name for selected zone, e.g. "North Gondar"
  language: LanguageKey;

  // Map drill-down state
  mapDrillRegion: string | null;

  // Whether forecast has been requested (user clicked "Generate")
  forecastRequested: boolean;

  // Actions
  setRegion: (key: string) => void;
  setSeason: (key: SeasonKey) => void;
  /** Set zone selection. Pass null to clear and return to region-level. */
  setZone: (key: string | null, display?: string | null) => void;
  setLanguage: (lang: LanguageKey) => void;
  setMapDrillRegion: (key: string | null) => void;
  requestForecast: () => void;
  reset: () => void;
}

const DEFAULT_STATE = {
  regionKey:          "amhara",
  seasonKey:          "Kiremt" as SeasonKey,
  zoneKey:            null,
  zoneDisplay:        null,
  language:           "en" as LanguageKey,
  mapDrillRegion:     null,
  forecastRequested:  false,
};

export const useSelectionStore = create<SelectionState>()(
  persist(
    (set) => ({
      ...DEFAULT_STATE,

      setRegion: (key) =>
        set({ regionKey: key, zoneKey: null, zoneDisplay: null, forecastRequested: false }),

      setSeason: (key) =>
        set({ seasonKey: key, forecastRequested: false }),

      setZone: (key, display = null) =>
        set({ zoneKey: key, zoneDisplay: key ? (display ?? null) : null, forecastRequested: false }),

      setLanguage: (lang) =>
        set({ language: lang }),

      setMapDrillRegion: (key) =>
        set({ mapDrillRegion: key }),

      requestForecast: () =>
        set({ forecastRequested: true }),

      reset: () => set(DEFAULT_STATE),
    }),
    {
      name: "azmera-selection",
      // skipHydration: server renders with defaults, client rehydrates
      // explicitly in <StoreHydration /> — prevents SSR/client mismatch.
      skipHydration: true,
      partialize: (state) => ({
        // Persist user preferences across page loads
        regionKey: state.regionKey,
        seasonKey: state.seasonKey,
        language:  state.language,
        // Do NOT persist zoneKey, forecastRequested, or mapDrillRegion
      }),
    }
  )
);
