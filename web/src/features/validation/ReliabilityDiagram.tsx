"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { SeasonKey } from "@/types/forecast";
import type { ReliabilityPoint } from "@/types/validation";
import { useReliabilityData } from "@/hooks/useValidation";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatPct } from "@/utils/format";

interface Props {
  region: string;
  season: SeasonKey;
}

interface CustomDotProps {
  cx?: number;
  cy?: number;
  payload?: ReliabilityPoint;
}

/** Scale dot radius by sample count: min 4, max 14. */
function dotRadius(n: number, maxN: number): number {
  if (maxN === 0) return 6;
  return 4 + (n / maxN) * 10;
}

interface TooltipPayload {
  payload: ReliabilityPoint;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayload[];
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const pt = payload[0].payload;
  return (
    <div className="bg-background-elevated border border-background-border rounded-lg px-3 py-2 shadow-lg text-xs space-y-1">
      <p className="text-text-secondary">
        Forecast prob:{" "}
        <span className="font-mono font-semibold text-text-primary">
          {formatPct(pt.forecast_prob)}
        </span>
      </p>
      <p className="text-text-secondary">
        Observed freq:{" "}
        <span className="font-mono font-semibold text-text-primary">
          {formatPct(pt.observed_freq)}
        </span>
      </p>
      <p className="text-text-muted">n = {pt.n}</p>
    </div>
  );
}

function CustomDot(props: CustomDotProps & { maxN: number }) {
  const { cx, cy, payload, maxN } = props;
  if (cx === undefined || cy === undefined || !payload) return null;
  const r = dotRadius(payload.n, maxN);
  return (
    <circle
      cx={cx}
      cy={cy}
      r={r}
      fill="#4a90d9"
      fillOpacity={0.75}
      stroke="#6aaef7"
      strokeWidth={1}
    />
  );
}

function SkeletonDiagram() {
  return (
    <div className="w-full h-[240px] sm:h-[320px] flex items-center justify-center bg-background-elevated rounded-xl border border-background-border animate-pulse">
      <span className="text-text-muted text-sm">Loading reliability data…</span>
    </div>
  );
}

export function ReliabilityDiagram({ region, season }: Props) {
  const { data, isLoading, error } = useReliabilityData(region, season);

  if (isLoading) return <SkeletonDiagram />;

  if (error) {
    return (
      <div className="w-full h-[240px] sm:h-[320px] flex items-center justify-center rounded-xl border border-background-border">
        <p className="text-red-400 text-sm">Failed to load reliability data.</p>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <EmptyState title="No reliability data for this region" />
    );
  }

  const maxN = Math.max(...data.map((d) => d.n));

  return (
    <div className="rounded-xl border border-background-border bg-background-card p-4">
      <h3 className="text-sm font-semibold text-text-secondary mb-1 uppercase tracking-wider">
        Reliability Diagram
      </h3>
      <p className="text-xs text-text-muted mb-4">
        Perfect calibration = points on diagonal
      </p>

      <div className="h-[220px] sm:h-[300px]">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 24, bottom: 32, left: 8 }}>
          <CartesianGrid stroke="#1a2030" strokeDasharray="3 3" />
          <XAxis
            type="number"
            dataKey="forecast_prob"
            domain={[0, 1]}
            tickCount={6}
            label={{
              value: "Forecast Probability",
              position: "insideBottom",
              offset: -16,
              fill: "#7a90a8",
              fontSize: 11,
            }}
            tick={{ fill: "#7a90a8", fontSize: 11 }}
            axisLine={{ stroke: "#1a2030" }}
            tickLine={{ stroke: "#1a2030" }}
          />
          <YAxis
            type="number"
            dataKey="observed_freq"
            domain={[0, 1]}
            tickCount={6}
            label={{
              value: "Observed Frequency",
              angle: -90,
              position: "insideLeft",
              offset: 8,
              fill: "#7a90a8",
              fontSize: 11,
            }}
            tick={{ fill: "#7a90a8", fontSize: 11 }}
            axisLine={{ stroke: "#1a2030" }}
            tickLine={{ stroke: "#1a2030" }}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: "3 3", stroke: "#3d5166" }} />

          {/* Perfect reliability diagonal via two reference lines acting as a visual */}
          <ReferenceLine
            segment={[
              { x: 0, y: 0 },
              { x: 1, y: 1 },
            ]}
            stroke="#3d5166"
            strokeDasharray="6 3"
            label={{
              value: "Perfect",
              position: "insideTopLeft",
              fill: "#3d5166",
              fontSize: 10,
            }}
          />

          <Scatter
            data={data}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            shape={(props: any) => <CustomDot {...props} maxN={maxN} />}
          />
        </ScatterChart>
      </ResponsiveContainer>
      </div>
    </div>
  );
}
