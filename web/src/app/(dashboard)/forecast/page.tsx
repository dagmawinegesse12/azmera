import type { Metadata } from "next";
import { ForecastPanel } from "@/features/forecast/ForecastPanel";
import { RegionSeasonSelector } from "@/features/forecast/RegionSeasonSelector";

export const metadata: Metadata = {
  title: "Forecast · Azmera",
};

export default function ForecastPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-semibold text-text-primary">Seasonal Forecast</h1>
        <p className="text-text-muted text-sm mt-1">
          Select a region and season to generate a probabilistic rainfall forecast.
        </p>
      </div>
      <RegionSeasonSelector />
      <ForecastPanel />
    </div>
  );
}
