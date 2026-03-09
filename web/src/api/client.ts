// ── API client ────────────────────────────────────────────────────
// All frontend API calls go through Next.js API routes (/api/...).
// This client never calls the Python backend directly.
// The Next.js API routes proxy to the Python FastAPI server.

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly detail?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `/api${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    let detail: unknown;
    try { detail = await res.json(); } catch { /* ignore */ }
    throw new ApiError(res.status, `API error ${res.status}: ${url}`, detail);
  }

  return res.json() as Promise<T>;
}

function buildParams(obj: Record<string, string | number | boolean | undefined>): string {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined) params.set(k, String(v));
  }
  const s = params.toString();
  return s ? `?${s}` : "";
}

export const api = {
  get: <T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> =>
    apiFetch<T>(`${path}${params ? buildParams(params) : ""}`),
  post: <T>(path: string, body: unknown): Promise<T> =>
    apiFetch<T>(path, { method: "POST", body: JSON.stringify(body) }),
};
