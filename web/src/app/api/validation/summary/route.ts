import type { NextRequest } from "next/server";
import { proxyToBackend, missingParams } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest): Promise<Response> {
  const { searchParams } = req.nextUrl;
  const season = searchParams.get("season") ?? undefined;

  if (!season) return missingParams(["season"]);

  return proxyToBackend({
    path:   "/validation/summary",
    params: { season },
    label:  "validation/summary",
  });
}
