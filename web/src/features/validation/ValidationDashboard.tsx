"use client";

import { useState } from "react";
import type { SeasonKey } from "@/types/forecast";
import type { ValidationSummary } from "@/types/validation";
import { useValidationSummary } from "@/hooks/useValidation";
import { REGION_OPTIONS } from "@/constants/regions";
import { formatHss } from "@/utils/format";
import { useLocale } from "@/hooks/useLocale";
import { ReleaseMatrixTable } from "./ReleaseMatrixTable";
import { HSSByRegionChart } from "./HSSByRegionChart";
import { ReliabilityDiagram } from "./ReliabilityDiagram";

const SEASON_OPTIONS: SeasonKey[] = ["Kiremt", "Belg", "OND", "Bega"];

interface SummaryCardProps {
  label: string;
  value: string | number;
  accent?: "green" | "amber" | "red" | "blue";
  isLoading?: boolean;
}

const ACCENT_CLASSES: Record<NonNullable<SummaryCardProps["accent"]>, string> = {
  green: "text-emerald-400",
  amber: "text-amber-400",
  red: "text-red-400",
  blue: "text-sky-400",
};

function SummaryCard({ label, value, accent = "blue", isLoading }: SummaryCardProps) {
  return (
    <div className="flex-1 min-w-[140px] rounded-xl border border-background-border bg-background-card p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
        {label}
      </p>
      {isLoading ? (
        <div className="h-7 w-16 rounded bg-background-elevated animate-pulse" />
      ) : (
        <p className={`text-2xl font-bold tabular-nums ${ACCENT_CLASSES[accent]}`}>
          {value}
        </p>
      )}
    </div>
  );
}

function hssAccent(hss: number): SummaryCardProps["accent"] {
  if (hss >= 0.1) return "green";
  if (hss > 0) return "amber";
  return "red";
}

function HSSNote({ summary }: { summary: ValidationSummary }) {
  const t = useLocale();
  const roSign = summary.aggregate_hss >= 0 ? "+" : "";
  const cvSign = summary.loocv_hss >= 0 ? "+" : "";
  return (
    <div className="rounded-lg border border-background-border bg-background-elevated px-4 py-2.5 text-xs text-text-secondary">
      <span className="font-semibold text-text-primary">{t.validation.skillScores} </span>
      {t.validation.roHssProspective}:{" "}
      <span className="font-mono font-semibold text-emerald-400">
        {roSign}{formatHss(summary.aggregate_hss)}
      </span>
      {" · "}
      {t.validation.loocvHssOptimistic}:{" "}
      <span className="font-mono font-semibold text-sky-400">
        {cvSign}{formatHss(summary.loocv_hss)}
      </span>
      <span className="ml-2 text-text-muted">
        {t.validation.hssNote}
      </span>
    </div>
  );
}

export function ValidationDashboard() {
  const [season, setSeason] = useState<SeasonKey>("Kiremt");
  const [selectedRegion, setSelectedRegion] = useState<string>(
    REGION_OPTIONS[0]?.key ?? ""
  );
  const t = useLocale();

  const { data: summary, isLoading: summaryLoading } = useValidationSummary(season);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-text-primary">{t.validation.sectionTitle}</h2>
          <p className="text-sm text-text-muted mt-0.5">
            {t.validation.sectionDescription}
          </p>
        </div>

        {/* Season selector */}
        <div className="flex items-center gap-2">
          <label
            htmlFor="season-select"
            className="text-xs font-semibold uppercase tracking-wider text-text-muted whitespace-nowrap"
          >
            {t.validation.seasonLabel}
          </label>
          <select
            id="season-select"
            value={season}
            onChange={(e) => setSeason(e.target.value as SeasonKey)}
            className="rounded-lg border border-background-border bg-background-elevated text-text-primary text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-sky-500/40 cursor-pointer"
          >
            {SEASON_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Summary cards */}
      <div className="flex flex-wrap gap-3">
        <SummaryCard
          label={t.validation.aggregateRoHss}
          value={summary ? formatHss(summary.aggregate_hss) : "—"}
          accent={summary ? hssAccent(summary.aggregate_hss) : "blue"}
          isLoading={summaryLoading}
        />
        <SummaryCard
          label={t.validation.fullRelease}
          value={summary?.n_full ?? "—"}
          accent="green"
          isLoading={summaryLoading}
        />
        <SummaryCard
          label={t.validation.experimental}
          value={summary?.n_experimental ?? "—"}
          accent="amber"
          isLoading={summaryLoading}
        />
        <SummaryCard
          label={t.validation.suppressed}
          value={summary?.n_suppressed ?? "—"}
          accent="red"
          isLoading={summaryLoading}
        />
      </div>

      {/* HSS comparison note */}
      {summary && !summaryLoading && <HSSNote summary={summary} />}
      {summaryLoading && (
        <div className="h-10 rounded-lg bg-background-elevated animate-pulse" />
      )}

      {/* Release matrix table */}
      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">
          {t.validation.releaseMatrix}
        </h3>
        <ReleaseMatrixTable season={season} />
      </section>

      {/* HSS bar chart */}
      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">
          {t.validation.hssByRegion}
        </h3>
        <HSSByRegionChart season={season} />
      </section>

      {/* Reliability diagram with region selector */}
      <section className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">
            {t.validation.reliabilityDiagram}
          </h3>
          <div className="flex items-center gap-2">
            <label
              htmlFor="region-select"
              className="text-xs font-semibold uppercase tracking-wider text-text-muted whitespace-nowrap"
            >
              {t.validation.regionLabel}
            </label>
            <select
              id="region-select"
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              className="rounded-lg border border-background-border bg-background-elevated text-text-primary text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-sky-500/40 cursor-pointer"
            >
              {REGION_OPTIONS.map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <ReliabilityDiagram region={selectedRegion} season={season} />
      </section>
    </div>
  );
}
