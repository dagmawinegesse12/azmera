"use client";

import { AlertTriangle } from "lucide-react";
import type { LanguageKey, ReleaseTier } from "@/types/forecast";
import { formatHss } from "@/utils/format";
import { EmptyState } from "@/components/shared/EmptyState";
import { useLocale } from "@/hooks/useLocale";

interface AdvisoryCardProps {
  advisoryEn: string | null;
  advisoryAm: string | null;
  /** Language is driven by the global TopNav toggle (store.language). */
  language: LanguageKey;
  /** Release tier of the forecast — drives caution banner for experimental. */
  releaseTier?: ReleaseTier | null;
  /** Rolling-origin HSS — shown alongside caution banner for context. */
  roHss?: number | null;
}

/**
 * Parse advisory text into individual bullet strings.
 *
 * Gemini (like GPT-4o before it) can return several formats:
 *   • 🌦️ ...      ← bullet char (U+2022) — canonical after prompt fix
 *   - 🌱 ...      ← markdown dash
 *   * 💧 ...      ← markdown asterisk
 *   1. 🌾 ...     ← numbered list
 *   1) 🌾 ...     ← numbered paren variant
 *
 * We accept all of them defensively so cached responses still render.
 */
function parseBullets(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(
      (line) =>
        line.startsWith("•") ||
        line.startsWith("-") ||
        line.startsWith("*") ||
        /^\d+[.)]\s/.test(line)
    )
    .filter((line) => line.length > 3);
}

/** Strip the leading bullet/number/dash from a parsed line. */
function stripPrefix(bullet: string): string {
  return bullet.replace(/^(?:•|-|\*|\d+[.):])\s*/, "").trim();
}

export function AdvisoryCard({
  advisoryEn,
  advisoryAm,
  language,
  releaseTier,
  roHss,
}: AdvisoryCardProps) {
  const t = useLocale();

  // Language is controlled globally — no local toggle state
  const advisory = language === "am" ? advisoryAm : advisoryEn;
  const hasAdvisory = advisory && advisory.trim().length > 0;
  const bullets = hasAdvisory ? parseBullets(advisory) : [];
  const showRaw = hasAdvisory && bullets.length === 0;

  const isExperimental = releaseTier === "experimental";

  return (
    <div className="bg-background-surface rounded-xl p-5 border border-background-border flex flex-col gap-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-primary uppercase tracking-wide">
          {t.advisory.title}
        </h3>
      </div>

      {/* Experimental-tier caution banner */}
      {isExperimental && (
        <div className="flex gap-2.5 p-3 rounded-lg bg-amber-950/30 border border-amber-700/30 text-xs text-amber-200 leading-relaxed">
          <AlertTriangle size={14} className="shrink-0 mt-0.5 text-amber-400" aria-hidden="true" />
          <span>
            <strong className="font-semibold text-amber-300">{t.advisory.experimentalBadge}</strong>
            {" — "}
            {t.advisory.experimentalNote}
            {roHss != null ? ` (RO-HSS: ${formatHss(roHss)})` : ""}.
            {" "}{t.advisory.experimentalAction}
          </span>
        </div>
      )}

      {/* Advisory content */}
      {!hasAdvisory ? (
        <EmptyState title={t.advisory.noAdvisory} />
      ) : showRaw ? (
        <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-line">
          {advisory}
        </p>
      ) : (
        <ul className="flex flex-col gap-2.5">
          {bullets.map((bullet, idx) => (
            <li
              key={idx}
              className="text-sm text-text-secondary leading-relaxed flex gap-2"
            >
              <span className="text-text-faint shrink-0" aria-hidden="true">
                •
              </span>
              <span>{stripPrefix(bullet)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
