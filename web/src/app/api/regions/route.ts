import type { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/proxy";

export const dynamic = "force-dynamic";

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function GET(_req: NextRequest): Promise<Response> {
  return proxyToBackend({ path: "/regions", label: "regions" });
}
