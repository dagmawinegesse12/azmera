"use client";

import { useLocale } from "@/hooks/useLocale";

/**
 * Client component wrapper for the Validation page heading.
 * Reads from the global locale so it responds to the language toggle.
 * The parent page stays a Server Component (for metadata export).
 */
export function ValidationPageHeading() {
  const t = useLocale();
  return (
    <div>
      <h1 className="text-xl sm:text-2xl font-semibold text-text-primary">
        {t.validationPage.title}
      </h1>
      <p className="text-text-muted text-sm mt-1">
        {t.validationPage.description}
      </p>
    </div>
  );
}
