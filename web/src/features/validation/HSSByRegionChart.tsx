"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from "recharts";
import type { SeasonKey } from "@/types/forecast";
import type { ReleaseMatrixRow } from "@/types/validation";
import { useReleaseMatrix } from "@/hooks/useValidation";
import { formatHss } from "@/utils/format";

interface Props {
  season: SeasonKey;
}

function barFill(hss: number): string {
  if (hss >= 0.1) return "#27ae60";
  if (hss > 0) return "#d4a017";
  return "#e74c3c";
}

interface TooltipPayload {
  payload: ReleaseMatrixRow;
  value: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayload[];
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const row = payload[0].payload;
  const hss = payload[0].value;
  return (
    <div className="bg-background-elevated border border-background-border rounded-lg px-3 py-2 shadow-lg text-xs">
      <p className="font-semibold text-text-primary mb-1">{row.region_display}</p>
      <p className="text-text-secondary">
        RO-HSS:{" "}
        <span
          style={{ color: barFill(hss) }}
          className="font-mono font-semibold"
        >
          {formatHss(hss)}
        </span>
      </p>
    </div>
  );
}

function SkeletonChart() {
  return (
    <div className="w-full h-[260px] sm:h-[400px] flex items-center justify-center bg-background-elevated rounded-xl border border-background-border animate-pulse">
      <span className="text-text-muted text-sm">Loading chart…</span>
    </div>
  );
}

export function HSSByRegionChart({ season }: Props) {
  const { data, isLoading, error } = useReleaseMatrix(season);

  if (isLoading) return <SkeletonChart />;

  if (error) {
    return (
      <div className="w-full h-[260px] sm:h-[400px] flex items-center justify-center rounded-xl border border-background-border">
        <p className="text-red-400 text-sm">Failed to load chart data.</p>
      </div>
    );
  }

  const sorted = [...(data ?? [])].sort((a, b) => b.ro_hss - a.ro_hss);

  return (
    <div className="rounded-xl border border-background-border bg-background-card p-4">
      <h3 className="text-sm font-semibold text-text-secondary mb-4 uppercase tracking-wider">
        RO-HSS by Region — {season}
      </h3>
      <div className="h-[240px] sm:h-[380px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={sorted}
          layout="vertical"
          margin={{ top: 4, right: 32, left: 8, bottom: 4 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#1a2030"
            horizontal={false}
          />
          <XAxis
            type="number"
            domain={[-0.2, 0.5]}
            tickCount={8}
            tick={{ fill: "#7a90a8", fontSize: 11 }}
            axisLine={{ stroke: "#1a2030" }}
            tickLine={{ stroke: "#1a2030" }}
          />
          <YAxis
            type="category"
            dataKey="region_display"
            width={110}
            tick={{ fill: "#7a90a8", fontSize: 11 }}
            axisLine={{ stroke: "#1a2030" }}
            tickLine={false}
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ fill: "rgba(255,255,255,0.03)" }}
          />
          <ReferenceLine
            x={0}
            stroke="#3d5166"
            strokeDasharray="4 4"
          />
          <ReferenceLine
            x={0.1}
            stroke="#27ae60"
            strokeDasharray="4 4"
            label={{
              value: "Threshold",
              position: "insideTopRight",
              fill: "#27ae60",
              fontSize: 10,
            }}
          />
          <Bar dataKey="ro_hss" radius={[0, 3, 3, 0]} maxBarSize={16}>
            {sorted.map((row) => (
              <Cell
                key={row.region_key}
                fill={barFill(row.ro_hss)}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      </div>
    </div>
  );
}
