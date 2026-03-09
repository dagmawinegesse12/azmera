import type { Metadata } from "next";
import { MapWithDrillDown } from "@/features/map/MapWithDrillDown";

export const metadata: Metadata = {
  title: "Risk Map · Azmera",
};

export default function MapPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-semibold text-text-primary">Regional Risk Map</h1>
        <p className="text-text-muted text-sm mt-1">
          Click a region to drill into its zone-level forecasts. Colors show the dominant rainfall outlook.
        </p>
      </div>
      {/* MapWithDrillDown is a client component — reads season from store,
          handles region clicks, and renders RegionDrillDown panel. */}
      <MapWithDrillDown />
    </div>
  );
}
