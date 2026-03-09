"use client";

import { SignalValue } from "@/types/forecast";

interface SignalPillProps {
  label: string;
  signal: SignalValue | null;
  compact?: boolean;
}

function phaseColor(phase: string): string {
  if (phase.includes("El Niño") || phase.includes("Positive")) {
    return "#d4a017";
  }
  if (phase.includes("La Niña") || phase.includes("Negative")) {
    return "#27ae60";
  }
  return "#6b7280"; // muted neutral
}

function formatValue(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}°`;
}

export function SignalPill({ label, signal, compact = false }: SignalPillProps) {
  const textSizeClass = compact ? "text-xs" : "text-sm";
  const paddingClass = compact ? "px-2 py-0.5" : "px-3 py-1";
  const valueSizeClass = compact ? "text-[10px]" : "text-xs";

  if (!signal) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 ${paddingClass} rounded-full bg-background-elevated border border-background-border ${textSizeClass} text-text-muted`}
      >
        <span className="font-medium">{label}</span>
        <span className={valueSizeClass}>—</span>
      </span>
    );
  }

  const color = phaseColor(signal.phase);

  return (
    <span
      className={`inline-flex items-center gap-1.5 ${paddingClass} rounded-full bg-background-elevated border border-background-border ${textSizeClass}`}
      title={signal.description}
    >
      <span className="font-medium text-text-secondary">{label}</span>
      <span style={{ color }} className="font-semibold">
        {signal.phase}
      </span>
      <span className={`${valueSizeClass} text-text-faint`}>
        {formatValue(signal.value)}
      </span>
    </span>
  );
}
