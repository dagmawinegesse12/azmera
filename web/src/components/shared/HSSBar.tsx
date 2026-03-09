"use client";

const BAR_POSITIVE = "#27ae60";
const BAR_NEGATIVE = "#e74c3c";

interface HSSBarProps {
  hss: number;
  maxHss?: number;
  label?: string;
  showValue?: boolean;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export function HSSBar({
  hss,
  maxHss = 1,
  label,
  showValue = true,
}: HSSBarProps) {
  const clamped = clamp(hss, -1, 1);
  const effectiveMax = clamp(maxHss, 0.01, 1);

  // Fraction of half-width the bar occupies (0–1 per side)
  const fraction = Math.abs(clamped) / effectiveMax;
  const halfPct  = clamp(fraction * 50, 0, 50);

  const isPositive = clamped >= 0;
  const barColor   = isPositive ? BAR_POSITIVE : BAR_NEGATIVE;

  // Positive: starts at 50% center, extends right
  // Negative: ends at 50% center, extends left
  const barLeft  = isPositive ? "50%" : `${50 - halfPct}%`;
  const barWidth = `${halfPct}%`;

  const sign = clamped >= 0 ? "+" : "";

  return (
    <div className="flex w-full flex-col gap-1">
      {/* Label row */}
      {(label !== undefined || showValue) && (
        <div className="flex items-center justify-between">
          {label !== undefined && (
            <span className="text-xs text-text-muted">{label}</span>
          )}
          {showValue && (
            <span
              className="ml-auto text-xs font-medium tabular-nums"
              style={{ color: barColor }}
            >
              {sign}{clamped.toFixed(2)}
            </span>
          )}
        </div>
      )}

      {/* Track */}
      <div className="relative h-3 w-full overflow-hidden rounded bg-background-elevated">
        {/* Filled bar */}
        <div
          className="absolute top-0 h-full rounded"
          style={{
            left:            barLeft,
            width:           barWidth,
            backgroundColor: barColor,
          }}
        />

        {/* Zero line */}
        <div
          className="absolute top-0 h-full w-px bg-text-faint/60"
          style={{ left: "50%" }}
        />
      </div>
    </div>
  );
}
