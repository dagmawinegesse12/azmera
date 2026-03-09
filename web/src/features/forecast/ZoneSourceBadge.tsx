"use client";

/**
 * ZoneSourceBadge — small inline badge indicating whether the zone forecast
 * comes from a zone-specific model or is a region-level fallback.
 *
 * source="zone"            → teal "Zone Model" badge
 * source="region_fallback" → amber "Region Fallback" badge + optional reason
 */

interface Props {
  source: "zone" | "region_fallback";
  fallbackReason?: string | null;
}

export function ZoneSourceBadge({ source, fallbackReason }: Props) {
  if (source === "zone") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-teal-900/40 border border-teal-600/40 text-teal-300">
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-teal-400" />
        Zone Model
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-900/40 border border-amber-600/40 text-amber-300"
      title={fallbackReason ?? "No zone-specific model — using regional forecast"}
    >
      <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-400" />
      Region Fallback
      {fallbackReason && (
        <span className="font-normal text-amber-400/80">— {fallbackReason}</span>
      )}
    </span>
  );
}
