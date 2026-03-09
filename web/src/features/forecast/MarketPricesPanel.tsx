"use client";

import { useMarketPrices } from "@/hooks/useForecast";
import { useSelectionStore } from "@/store/selectionStore";
import { formatEtb } from "@/utils/format";
import { EmptyState } from "@/components/shared/EmptyState";
import { REGION_DISPLAY } from "@/constants/regions";
import type { RegionKey } from "@/constants/regions";

interface MarketPricesPanelProps {
  /** Optional note shown below the header (e.g. scope clarification for zone forecasts). */
  scopeNote?: string;
}

function SkeletonRow() {
  return (
    <div className="flex items-center gap-3 py-2 animate-pulse">
      <div className="h-3 w-28 rounded bg-background-border" />
      <div className="h-3 w-16 rounded bg-background-border" />
      <div className="h-3 w-12 rounded bg-background-border ml-auto" />
    </div>
  );
}

export function MarketPricesPanel({ scopeNote }: MarketPricesPanelProps = {}) {
  // Store field is "regionKey", not "region"
  const { regionKey: region } = useSelectionStore();
  const { data, isLoading, error } = useMarketPrices();

  // Use human-readable display name; fall back to raw key only if lookup fails
  const regionLabel = region
    ? (REGION_DISPLAY[region as RegionKey] ?? region)
    : "Selected Region";

  return (
    <div className="bg-background-surface rounded-xl p-5 border border-background-border flex flex-col gap-4">
      {/* Header */}
      <div className="flex flex-col gap-0.5">
        <h3 className="text-sm font-semibold text-text-primary uppercase tracking-wide">
          Market Prices — {regionLabel}
        </h3>
        {data && data.length > 0 && (
          <p className="text-xs text-text-muted">{data[0].market_name}</p>
        )}
        {scopeNote && (
          <p className="text-xs text-amber-400/70 italic mt-0.5">{scopeNote}</p>
        )}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex flex-col divide-y divide-background-border">
          <SkeletonRow />
          <SkeletonRow />
          <SkeletonRow />
        </div>
      ) : error ? (
        <p className="text-sm text-text-muted">Price data unavailable</p>
      ) : !data || data.length === 0 ? (
        <EmptyState title="No price data available" />
      ) : (
        <div className="overflow-x-auto -mx-1">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-left text-xs text-text-muted uppercase tracking-wide">
                <th className="pb-2 pr-4 font-medium">Commodity</th>
                <th className="pb-2 pr-4 font-medium text-right">
                  Price (ETB)
                </th>
                <th className="pb-2 font-medium text-right">Change</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-background-border">
              {data.map((row, idx) => {
                // price_change_pct can be null when no prior month data exists
                const hasPct = row.price_change_pct != null;
                const pct = row.price_change_pct ?? 0;
                const changeColor =
                  pct < 0 ? "text-forecast-below" : "text-forecast-above";
                const changeSign = pct >= 0 ? "+" : "";

                return (
                  <tr key={idx} className="group">
                    <td className="py-2 pr-4 text-text-secondary font-medium">
                      {row.commodity}
                    </td>
                    <td className="py-2 pr-4 text-right font-mono text-text-primary">
                      {formatEtb(row.price_etb)}
                    </td>
                    <td
                      className={`py-2 text-right font-mono font-semibold ${hasPct ? changeColor : "text-text-muted"}`}
                    >
                      {hasPct ? `${changeSign}${pct.toFixed(1)}%` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {data[0]?.date && (
            <p className="mt-3 text-xs text-text-faint">
              Data as of {data[0].date}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
