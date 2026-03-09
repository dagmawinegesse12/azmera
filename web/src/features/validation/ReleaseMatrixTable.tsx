"use client";

import { useState, useMemo } from "react";
import type { SeasonKey } from "@/types/forecast";
import type { ReleaseMatrixRow } from "@/types/validation";
import { useReleaseMatrix } from "@/hooks/useValidation";
import { SkillTierBadge } from "@/components/shared/SkillTierBadge";
import { HSSBar } from "@/components/shared/HSSBar";
import { formatHss } from "@/utils/format";

type SortKey = keyof Pick<ReleaseMatrixRow, "ro_hss" | "cv_hss" | "n_test_years" | "region_display">;
type SortDir = "asc" | "desc";

interface Props {
  season: SeasonKey;
}

function hssColorClass(hss: number): string {
  if (hss >= 0.1) return "text-emerald-400";
  if (hss > 0) return "text-amber-400";
  return "text-red-400";
}

function SkeletonRow() {
  return (
    <tr className="border-b border-background-border animate-pulse">
      {[1, 2, 3, 4, 5].map((i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-background-elevated rounded w-full" />
        </td>
      ))}
    </tr>
  );
}

export function ReleaseMatrixTable({ season }: Props) {
  const { data, isLoading, error } = useReleaseMatrix(season);
  const [sortKey, setSortKey] = useState<SortKey>("ro_hss");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const sorted = useMemo<ReleaseMatrixRow[]>(() => {
    if (!data) return [];
    return [...data].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const cmp =
        typeof av === "string" && typeof bv === "string"
          ? av.localeCompare(bv)
          : (av as number) - (bv as number);
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  function SortIcon({ col }: { col: SortKey }) {
    if (col !== sortKey) return <span className="ml-1 text-text-muted opacity-40">↕</span>;
    return (
      <span className="ml-1 text-text-secondary">
        {sortDir === "asc" ? "↑" : "↓"}
      </span>
    );
  }

  const headerCellClass =
    "px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-muted cursor-pointer select-none hover:text-text-primary transition-colors whitespace-nowrap";

  return (
    <div className="rounded-xl border border-background-border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-background-elevated sticky top-0 z-10">
            <tr>
              <th
                className={headerCellClass}
                onClick={() => handleSort("region_display")}
              >
                Region <SortIcon col="region_display" />
              </th>
              <th
                className={headerCellClass}
                onClick={() => handleSort("ro_hss")}
              >
                RO-HSS <SortIcon col="ro_hss" />
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-muted whitespace-nowrap">
                Tier
              </th>
              <th
                className={headerCellClass}
                onClick={() => handleSort("cv_hss")}
              >
                CV-HSS <SortIcon col="cv_hss" />
              </th>
              <th
                className={headerCellClass}
                onClick={() => handleSort("n_test_years")}
              >
                Test Years <SortIcon col="n_test_years" />
              </th>
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} />)}

            {error && (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-8 text-center text-red-400 text-sm"
                >
                  Failed to load release matrix data.
                </td>
              </tr>
            )}

            {!isLoading &&
              !error &&
              sorted.map((row) => (
                <tr
                  key={row.region_key}
                  className="border-b border-background-border hover:bg-background-elevated/50 transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-text-primary whitespace-nowrap">
                    {row.region_display}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3 min-w-[140px]">
                      <span className={`font-mono text-xs font-semibold w-12 shrink-0 ${hssColorClass(row.ro_hss)}`}>
                        {formatHss(row.ro_hss)}
                      </span>
                      <HSSBar value={row.ro_hss} />
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <SkillTierBadge tier={row.tier} />
                  </td>
                  <td className={`px-4 py-3 font-mono text-xs ${hssColorClass(row.cv_hss)}`}>
                    {formatHss(row.cv_hss)}
                  </td>
                  <td className="px-4 py-3 text-text-secondary text-xs tabular-nums">
                    {row.n_test_years}
                  </td>
                </tr>
              ))}

            {!isLoading && !error && sorted.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-8 text-center text-text-muted text-sm"
                >
                  No data available for {season}.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="px-4 py-2.5 bg-background-elevated border-t border-background-border">
        <p className="text-xs text-text-muted">
          Release tier assigned by rolling-origin HSS only. CV-HSS shown for reference.
        </p>
      </div>
    </div>
  );
}
