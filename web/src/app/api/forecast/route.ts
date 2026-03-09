import type { NextRequest } from "next/server";
import { proxyToBackend, missingParams } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest): Promise<Response> {
  const { searchParams } = req.nextUrl;
  const region = searchParams.get("region") ?? undefined;
  const season = searchParams.get("season") ?? undefined;
  const lang   = searchParams.get("lang")   ?? "en";

  if (!region || !season) return missingParams(["region", "season"]);

  return proxyToBackend({
    path:   "/forecast",
    params: { region, season, lang },
    label:  "forecast",
  });
}
