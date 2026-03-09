import type { NextRequest } from "next/server";
import { proxyToBackend, missingParams } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest): Promise<Response> {
  const { searchParams } = new URL(req.url);
  const region = searchParams.get("region") ?? undefined;

  if (!region) return missingParams(["region"]);

  return proxyToBackend({
    path:   "/zones",
    params: { region },
    label:  "zones",
  });
}
