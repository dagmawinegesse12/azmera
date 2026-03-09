# Azmera Frontend — Integration Notes

## Quick Start

```bash
cd web
cp .env.example .env.local
# Edit .env.local → set PYTHON_API_BASE to your backend URL
npm install
npm run dev
```

The app runs on `http://localhost:3000`. It requires the Python backend to be running (default: `http://localhost:8000`).

---

## Architecture Overview

```
Browser  →  Next.js (port 3000)  →  /api/* routes  →  Python backend (port 8000)
```

All frontend data fetching goes through Next.js API routes (`src/app/api/`), which act as a thin proxy. The browser never calls the Python backend directly, which eliminates CORS issues.

---

## Required Backend Endpoints

The following Python endpoints must exist. All return JSON.

| Next.js route | Python endpoint | Params |
|---|---|---|
| `GET /api/forecast` | `GET /forecast` | `region`, `season`, `lang` |
| `GET /api/forecast/zone` | `GET /forecast/zone` | `zone`, `zone_display`, `region`, `season`, `lang` |
| `GET /api/forecast/all` | `GET /forecast/all` | `season` |
| `GET /api/forecast/zones` | `GET /forecast/zones` | `region`, `season` |
| `GET /api/signals` | `GET /signals` | — |
| `GET /api/chirps-anomaly` | `GET /chirps-anomaly` | `region`, `season` |
| `GET /api/prices` | `GET /prices` | `region` |
| `GET /api/validation/summary` | `GET /validation/summary` | `season` |
| `GET /api/validation/timeline` | `GET /validation/timeline` | `region`, `season` |
| `GET /api/validation/reliability` | `GET /validation/reliability` | `region`, `season` |
| `GET /api/validation/release-matrix` | `GET /validation/release-matrix` | `season` |
| `GET /api/regions` | `GET /regions` | — |

---

## Expected JSON Shapes

### `/forecast` response
```json
{
  "region": "tigray",
  "season": "Kiremt",
  "prediction": "Above Normal",
  "prob_below": 0.18,
  "prob_near": 0.26,
  "prob_above": 0.56,
  "confidence": 56,
  "cv_hss": 0.142,
  "ro_hss": 0.106,
  "release_tier": "full",
  "no_skill": false,
  "advisory_en": "• Above-normal rainfall is favoured for Tigray during Kiremt.\n• Prospects for good crop establishment are positive.",
  "advisory_am": "• ...")
  "enso_current": 1.2,
  "enso_phase": "El Niño"
}
```

### `/signals` response
```json
{
  "enso": { "value": 1.2, "phase": "El Niño", "label": "ENSO", "description": "Warm ENSO phase..." },
  "iod":  { "value": 0.3, "phase": "Neutral", "label": "IOD",  "description": "..." },
  "pdo":  { "value": -0.4, "phase": "Negative", "label": "PDO", "description": "..." },
  "atl":  { "value": 0.1, "phase": "Neutral", "label": "Atlantic SST", "description": "..." },
  "amm_jan": { "value": 0.8 },
  "fetched_at": "2026-03-08T10:00:00Z"
}
```

### `/validation/release-matrix` response
```json
[
  {
    "region_key": "tigray",
    "region_display": "Tigray",
    "ro_hss": 0.106,
    "cv_hss": 0.142,
    "tier": "full",
    "n_test_years": 27
  },
  ...
]
```

### `/validation/summary` response
```json
{
  "season": "Kiremt",
  "aggregate_hss": 0.063,
  "n_regions": 13,
  "n_full": 4,
  "n_experimental": 6,
  "n_suppressed": 3,
  "n_test_years": 27,
  "loocv_hss": 0.145
}
```

### `/validation/timeline` response
```json
[
  {
    "year": 2000,
    "actual": "Above Normal",
    "predicted": "Above Normal",
    "correct": true,
    "prob_below": 0.15,
    "prob_near": 0.30,
    "prob_above": 0.55
  },
  ...
]
```

### `/validation/reliability` response
```json
[
  { "forecast_prob": 0.33, "observed_freq": 0.28, "n": 25 },
  { "forecast_prob": 0.50, "observed_freq": 0.47, "n": 18 },
  ...
]
```

### `/chirps-anomaly` response
```json
{
  "region": "tigray",
  "season": "Kiremt",
  "anomaly_pct": 12.4,
  "anomaly_mm": 38.2,
  "tercile": "Above Normal",
  "z_score": 0.8
}
```

### `/prices` response
```json
[
  {
    "region": "tigray",
    "commodity": "Teff",
    "price_etb": 4200,
    "price_change_pct": 3.2,
    "market_name": "Mekelle Market",
    "date": "2026-02"
  }
]
```

---

## GeoJSON File

The map (`/map`) requires a static GeoJSON file at:
```
web/public/ethiopia_regions.geojson
```

Each feature must have:
```json
{
  "type": "Feature",
  "properties": {
    "name": "Tigray",
    "region_key": "tigray"
  },
  "geometry": { ... }
}
```

The `region_key` values must match the keys used in forecast data:
`addis_ababa`, `afar`, `amhara`, `benishangul_gumz`, `dire_dawa`, `gambela`, `harari`, `oromia`, `sidama`, `snnpr`, `somali`, `south_west`, `tigray`

A suitable GeoJSON can be sourced from GADM (gadm.org) or OCHA HDX at administrative level 1 for Ethiopia.

---

## State Management

- **Zustand** (`src/store/selectionStore.ts`) — persists `regionKey`, `seasonKey`, `language` to `localStorage` under the key `azmera-selection`.
- **TanStack Query** — all server state. Cache TTLs: 1 hour for forecasts/signals, 24 hours for validation data.
- The `forecastRequested` flag in Zustand gates all forecast queries. Queries are disabled until the user clicks "Generate Forecast".

---

## Release Tier Logic

Release tiers are computed **both** on the frontend (from hard-coded RO-HSS values in `src/constants/tiers.ts`) and confirmed by the backend (`release_tier` field in forecast response). The frontend constants are used for:
- Map colouring before a forecast is requested
- Displaying tier badges in the validation table
- The `getReleaseTier()` helper for any pure-frontend display logic

The backend response is authoritative for the actual forecast decision.

---

## Caching Notes

- Forecast API routes: `next: { revalidate: 3600 }` (1 hour)
- Validation API routes: `next: { revalidate: 86400 }` (24 hours)
- These are server-side Next.js data cache TTLs; TanStack Query also caches client-side with matching `staleTime` values.

---

## Adding a New Region

1. Add to `src/constants/regions.ts` — `REGION_KEYS`, `REGION_DISPLAY`, `REGION_OPTIONS`
2. Add RO-HSS values to `src/constants/tiers.ts` — `KIREMT_RO_HSS` and `BELG_RO_HSS`
3. Add the polygon to `public/ethiopia_regions.geojson` with matching `region_key`
4. Add the region to the Python backend's model registry

---

*Frontend written March 2026. Stack: Next.js 14 · React 18 · TypeScript · Tailwind CSS · Zustand · TanStack Query · Recharts · React-Leaflet.*
