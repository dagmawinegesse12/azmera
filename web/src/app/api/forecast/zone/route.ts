import type { NextRequest } from "next/server";
import { proxyToBackend, missingParams } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest): Promise<Response> {
  const { searchParams } = req.nextUrl;
  const zone         = searchParams.get("zone")         ?? undefined;
  const zone_display = searchParams.get("zone_display") ?? undefined;
  const region       = searchParams.get("region")       ?? undefined;
  const season       = searchParams.get("season")       ?? undefined;
  const lang         = searchParams.get("lang")         ?? "en";

  if (!zone || !region || !season) return missingParams(["zone", "region", "season"]);

  return proxyToBackend({
    path:   "/forecast/zone",
    params: { zone, zone_display, region, season, lang },
    label:  "forecast/zone",
  });
}
