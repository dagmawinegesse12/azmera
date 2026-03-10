"use client";

import { usePathname } from "next/navigation";
import { useSelectionStore } from "@/store/selectionStore";
import { FORECAST_SEASONS } from "@/constants/seasons";
import { useLocale } from "@/hooks/useLocale";
import type { Locale } from "@/hooks/useLocale";

// Maps URL pathnames to locale nav keys
const BREADCRUMB_KEYS: Record<string, "home" | "forecast" | "riskMap" | "validation"> = {
  "/":           "home",
  "/forecast":   "forecast",
  "/map":        "riskMap",
  "/validation": "validation",
};

function resolveBreadcrumb(pathname: string, t: Locale): string {
  const directKey = BREADCRUMB_KEYS[pathname];
  if (directKey) return t.nav[directKey];
  const prefix = Object.keys(BREADCRUMB_KEYS)
    .filter((k) => k !== "/")
    .find((k) => pathname.startsWith(k));
  return prefix ? t.nav[BREADCRUMB_KEYS[prefix]] : "Azmera";
}

export function TopNav() {
  const pathname    = usePathname();
  const season      = useSelectionStore((s) => s.seasonKey);
  const language    = useSelectionStore((s) => s.language);
  const setSeason   = useSelectionStore((s) => s.setSeason);
  const setLanguage = useSelectionStore((s) => s.setLanguage);
  const t           = useLocale();

  const breadcrumb = resolveBreadcrumb(pathname, t);

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-background-border bg-background-surface px-3 md:px-6">
      {/* Breadcrumb
          Mobile: show only the page name (space is tight)
          Desktop: show "Azmera / {Page}" */}
      <div className="flex items-center gap-2 min-w-0">
        <span className="hidden md:inline text-xs text-text-faint">Azmera</span>
        <span className="hidden md:inline text-xs text-text-faint">/</span>
        <span className="text-sm font-medium text-text-primary truncate">{breadcrumb}</span>
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Season selector */}
        <select
          value={season}
          onChange={(e) => setSeason(e.target.value as typeof season)}
          className="rounded border border-background-border bg-background-elevated px-2 py-1.5 text-xs md:text-sm text-text-primary outline-none focus:border-accent-green focus:ring-1 focus:ring-accent-green/40 transition-colors cursor-pointer"
        >
          {FORECAST_SEASONS.map((cfg) => (
            <option key={cfg.key} value={cfg.key}>
              {cfg.label}
            </option>
          ))}
        </select>

        {/* Language toggle — switches full site UI */}
        <button
          onClick={() => setLanguage(language === "en" ? "am" : "en")}
          className="rounded border border-background-border bg-background-elevated px-2.5 py-1.5 text-xs md:text-sm font-medium text-text-secondary transition-colors hover:border-accent-green/40 hover:text-text-primary"
          aria-label={t.topNav.toggleLanguage}
        >
          {language === "en" ? "EN" : "አማ"}
        </button>
      </div>
    </header>
  );
}
