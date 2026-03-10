// ── Locale hook ───────────────────────────────────────────────────────────────
// Returns the locale object for the user's current language setting.
// Usage:  const t = useLocale();  t.forecast.generateButton
//
// en.json is the type source of truth — am.json must be structurally identical.
// TypeScript enforces this via the `Locale` export below.

import { useSelectionStore } from "@/store/selectionStore";
import en from "@/locales/en.json";
import am from "@/locales/am.json";

export type Locale = typeof en;

// Cast am to Locale — both files are structurally identical (same keys, all strings).
const LOCALES: Record<string, Locale> = {
  en,
  am: am as unknown as Locale,
};

/**
 * Hook that returns the locale object for the current language.
 * Reads from the global Zustand selection store (persisted to localStorage).
 * Must only be called inside React components or other hooks.
 */
export function useLocale(): Locale {
  const language = useSelectionStore((s) => s.language);
  return LOCALES[language] ?? en;
}
