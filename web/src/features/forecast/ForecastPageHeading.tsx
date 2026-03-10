"use client";

import { useLocale } from "@/hooks/useLocale";

/**
 * Client component wrapper for the Forecast page heading.
 * Reads from the global locale so it responds to the language toggle.
 * The parent page stays a Server Component (for metadata export).
 */
export function ForecastPageHeading() {
  const t = useLocale();
  return (
    <div>
      <h1 className="text-xl sm:text-2xl font-semibold text-text-primary">
        {t.forecastPage.title}
      </h1>
      <p className="text-text-muted text-sm mt-1">
        {t.forecastPage.description}
      </p>
    </div>
  );
}
