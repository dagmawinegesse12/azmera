/**
 * Shared proxy helper for all Next.js API route handlers.
 *
 * Every route in /app/api/** should call proxyToBackend() instead of
 * hand-rolling fetch() so we get:
 *   - Consistent debug logging (backend URL, status, latency)
 *   - Non-200 responses surfaced in server logs (not silently swallowed)
 *   - Network errors with full error detail
 *   - A single place to adjust timeouts, headers, etc.
 */

const PYTHON_API = process.env.PYTHON_API_BASE ?? "http://127.0.0.1:8000";
const DEV = process.env.NODE_ENV !== "production";

/** Log only in development; kept terse for readability. */
function log(level: "info" | "warn" | "error", msg: string, ...args: unknown[]) {
  if (DEV) {
    const prefix = `[proxy:${level.toUpperCase()}]`;
    // eslint-disable-next-line no-console
    console[level === "info" ? "log" : level](prefix, msg, ...args);
  }
}

export interface ProxyOptions {
  /** Path on the Python backend, e.g. "/forecast/all" */
  path: string;
  /** Query string params object — all values coerced to string */
  params?: Record<string, string | undefined>;
  /** Label shown in logs, e.g. "forecast/all" */
  label?: string;
}

/**
 * Proxy a GET request to the Python FastAPI backend and return the
 * Next.js Response to send to the browser.
 *
 * Logs:
 *   → [proxy:INFO] GET http://127.0.0.1:8000/forecast/all?season=Kiremt
 *   ← [proxy:INFO] 200 OK  (42ms)
 *   ← [proxy:WARN] 422 Unprocessable Entity  (12ms)   ← non-200 surfaced
 *   ← [proxy:ERROR] fetch failed: connect ECONNREFUSED 127.0.0.1:8000
 */
export async function proxyToBackend(opts: ProxyOptions): Promise<Response> {
  const { path, params, label = path } = opts;

  // Build URL
  const qs = new URLSearchParams();
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) qs.set(k, v);
    }
  }
  const qstr = qs.toString();
  const url = `${PYTHON_API}${path}${qstr ? `?${qstr}` : ""}`;

  log("info", `→ GET ${url}   [backend: ${PYTHON_API}]`);
  const t0 = Date.now();

  try {
    const res = await fetch(url, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });

    const ms = Date.now() - t0;

    if (!res.ok) {
      // Surface non-200s as warnings so they show in Next.js server logs
      let body = "";
      try { body = await res.text(); } catch { /* ignore */ }
      log("warn", `← ${res.status} ${res.statusText}  (${ms}ms)  [${label}]  body: ${body.slice(0, 300)}`);
      return new Response(body || JSON.stringify({ error: `Backend returned ${res.status}` }), {
        status: res.status,
        headers: { "Content-Type": "application/json" },
      });
    }

    log("info", `← ${res.status} OK  (${ms}ms)  [${label}]`);
    const data = await res.json();
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });

  } catch (err) {
    const ms = Date.now() - t0;
    const msg = err instanceof Error ? err.message : String(err);
    log("error", `← fetch failed  (${ms}ms)  [${label}]: ${msg}`);
    log("error", `  Backend URL in use: ${PYTHON_API}`);
    log("error", `  Set PYTHON_API_BASE in web/.env.local to override`);

    return new Response(
      JSON.stringify({
        error: `Backend unreachable: ${label}`,
        detail: msg,
        backend_url: PYTHON_API,
      }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }
}

/** Convenience: return 400 JSON response for missing required params */
export function missingParams(fields: string[]): Response {
  return new Response(
    JSON.stringify({ error: `Missing required params: ${fields.join(", ")}` }),
    { status: 400, headers: { "Content-Type": "application/json" } }
  );
}
