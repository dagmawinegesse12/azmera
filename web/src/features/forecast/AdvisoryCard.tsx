"use client";

import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import type { LanguageKey, ReleaseTier } from "@/types/forecast";
import { formatHss } from "@/utils/format";
import { EmptyState } from "@/components/shared/EmptyState";

interface AdvisoryCardProps {
  advisoryEn: string | null;
  advisoryAm: string | null;
  language: LanguageKey;
  /** Release tier of the forecast — drives caution banner for experimental. */
  releaseTier?: ReleaseTier | null;
  /** Rolling-origin HSS — shown alongside caution banner for context. */
  roHss?: number | null;
}

/**
 * Parse advisory text into individual bullet strings.
 *
 * GPT-4o can return several formats depending on the prompt:
 *   • 🌦️ ...      ← bullet char (U+2022) — canonical after prompt fix
 *   - 🌱 ...      ← markdown dash
 *   * 💧 ...      ← markdown asterisk
 *   1. 🌾 ...     ← numbered list (old GPT-4o behavior before prompt fix)
 *   1) 🌾 ...     ← numbered paren variant
 *
 * We accept all of them defensively so old cached responses still render.
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
  const [activeLang, setActiveLang] = useState<LanguageKey>(language);

  const advisory = activeLang === "am" ? advisoryAm : advisoryEn;
  const hasAdvisory = advisory && advisory.trim().length > 0;
  const bullets = hasAdvisory ? parseBullets(advisory) : [];
  const showRaw = hasAdvisory && bullets.length === 0;

  const isExperimental = releaseTier === "experimental";

  return (
    <div className="bg-background-surface rounded-xl p-5 border border-background-border flex flex-col gap-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-primary uppercase tracking-wide">
          Advisory
        </h3>

        {/* Language toggle */}
        <div className="flex items-center rounded-md overflow-hidden border border-background-border text-xs font-medium">
          <button
            onClick={() => setActiveLang("en")}
            className={`px-2.5 py-1 transition-colors ${
              activeLang === "en"
                ? "bg-background-elevated text-text-primary"
                : "text-text-muted hover:text-text-secondary"
            }`}
            aria-pressed={activeLang === "en"}
          >
            EN
          </button>
          <button
            onClick={() => setActiveLang("am")}
            className={`px-2.5 py-1 transition-colors ${
              activeLang === "am"
                ? "bg-background-elevated text-text-primary"
                : "text-text-muted hover:text-text-secondary"
            }`}
            aria-pressed={activeLang === "am"}
          >
            አማ
          </button>
        </div>
      </div>

      {/* Experimental-tier caution banner */}
      {isExperimental && (
        <div className="flex gap-2.5 p-3 rounded-lg bg-amber-950/30 border border-amber-700/30 text-xs text-amber-200 leading-relaxed">
          <AlertTriangle size={14} className="shrink-0 mt-0.5 text-amber-400" aria-hidden="true" />
          <span>
            <strong className="font-semibold text-amber-300">Experimental forecast</strong>
            {" — "}
            Model skill is limited
            {roHss != null ? ` (RO-HSS: ${formatHss(roHss)})` : ""}.
            {" "}Treat recommendations as indicative only and verify with local
            agricultural extension officers and official sources before acting.
          </span>
        </div>
      )}

      {/* Advisory content */}
      {!hasAdvisory ? (
        <EmptyState title="No advisory available" />
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
