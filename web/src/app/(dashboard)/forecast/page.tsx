import type { Metadata } from "next";
import { ForecastPanel } from "@/features/forecast/ForecastPanel";
import { RegionSeasonSelector } from "@/features/forecast/RegionSeasonSelector";
import { ForecastPageHeading } from "@/features/forecast/ForecastPageHeading";

export const metadata: Metadata = {
  title: "Forecast · Azmera",
};

export default function ForecastPage() {
  return (
    <div className="space-y-6">
      <ForecastPageHeading />
      <RegionSeasonSelector />
      <ForecastPanel />
    </div>
  );
}
