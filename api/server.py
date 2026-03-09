"""
Azmera — REST API server (FastAPI)
Wraps the existing src/ Python functions and exposes them as JSON endpoints
for the React frontend to consume via the Next.js proxy layer.

Usage:
    cd /path/to/kiremtai
    uvicorn api.server:app --port 8000 --reload

Or via the helper script:
    python api/server.py
"""

import os
import sys
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("azmera.api")

# ── Path setup ────────────────────────────────────────────────────
# Allow `import forecaster` etc. from src/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR  = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import numpy as np
from sklearn.metrics import confusion_matrix as _confusion_matrix
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# ── Lazy-import heavy src modules ─────────────────────────────────
# NOTE: validation.py imports streamlit at module level so we NEVER import it.
# All validation logic needed here is inlined below.
import forecaster as _fc

# Optional imports — these modules have heavy Streamlit/geo deps.
# The API degrades gracefully if they are unavailable.
try:
    from chirps_anomaly import get_season_anomaly as _get_season_anomaly
    _CHIRPS_AVAILABLE = True
except Exception as _chirps_err:
    logger.warning("chirps_anomaly unavailable (%s) — /chirps-anomaly will return null", _chirps_err)
    _CHIRPS_AVAILABLE = False
    def _get_season_anomaly(region, season):  # type: ignore[misc]
        return None

# ── Inlined from map_component.get_all_forecasts ──────────────────
_ALL_REGIONS = [
    "tigray", "afar", "amhara", "oromia", "somali",
    "benishangul_gumz", "snnpr", "gambela", "harari",
    "dire_dawa", "addis_ababa", "sidama", "south_west",
]
_REGION_DISPLAY = {
    "tigray":           "Tigray",  "afar":             "Afar",
    "amhara":           "Amhara",  "oromia":           "Oromia",
    "somali":           "Somali",  "benishangul_gumz": "Benishangul Gumz",
    "snnpr":            "SNNPR",   "gambela":          "Gambela",
    "harari":           "Harari",  "dire_dawa":        "Dire Dawa",
    "addis_ababa":      "Addis Ababa",
    "sidama":           "Sidama",  "south_west":       "South West",
}

def _get_all_forecasts(season: str):
    results = []
    for key in _ALL_REGIONS:
        try:
            r = _fc.forecast(key, season, fast=True)
            r["region_key"]     = key
            r["region_display"] = _REGION_DISPLAY.get(key, key)
            # Add "tier" as alias for "release_tier" so the map component can use either
            r["tier"] = r.get("release_tier", "suppressed")
            results.append(r)
        except Exception as e:
            logger.warning("Fast forecast failed for %s/%s: %s", key, season, e)
    return results

# ── Inlined from validation.py (avoids its streamlit import) ──────
def _compute_hss(y_true, y_pred):
    """Heidke Skill Score for 3-class (Below/Near/Above) classification."""
    cm = _confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
    n        = cm.sum()
    if n == 0:
        return 0.0, cm
    correct  = np.diag(cm).sum()
    expected = sum(cm[i, :].sum() * cm[:, i].sum() for i in range(3)) / n
    denom    = n - expected
    return (float((correct - expected) / denom) if denom != 0 else 0.0), cm

# ── App setup ─────────────────────────────────────────────────────
app = FastAPI(
    title="Azmera API",
    description="Seasonal rainfall forecast API for Ethiopia",
    version="1.0.0",
)

# CORS — always allow localhost for dev; add production origin via env var.
# In production: set ALLOWED_ORIGINS=https://your-app.vercel.app
# Multiple origins: comma-separated, e.g. "https://a.vercel.app,https://b.vercel.app"
_CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
_extra = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
_CORS_ORIGINS.extend(_extra)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── Helper ────────────────────────────────────────────────────────
def _numpy_safe(obj):
    """Recursively convert numpy scalars/arrays to native Python types."""
    if isinstance(obj, dict):
        return {k: _numpy_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_numpy_safe(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, np.ndarray):
        return [_numpy_safe(v) for v in obj.tolist()]
    return obj

VALID_SEASONS = {"Kiremt", "Belg"}

def _validate_season(season: str):
    if season not in VALID_SEASONS:
        raise HTTPException(
            status_code=400,
            detail=f"season must be 'Kiremt' or 'Belg'; got '{season}'"
        )

# ── Indices / ocean signals ────────────────────────────────────────
@app.get("/signals")
def get_signals():
    """Latest ocean index values (ENSO, IOD, PDO, ATL, AMM)."""
    try:
        idx = _fc.get_latest_indices()
        amm = None
        try:
            amm = float(_fc.get_latest_amm_jan())
        except Exception:
            pass

        def _signal(arr, label, desc):
            val = float(arr[-1]) if len(arr) > 0 else 0.0
            if label == "ENSO":
                phase = "El Niño" if val > 0.5 else ("La Niña" if val < -0.5 else "Neutral")
            elif label == "IOD":
                phase = "Positive" if val > 0.4 else ("Negative" if val < -0.4 else "Neutral")
            elif label == "PDO":
                phase = "Positive" if val > 0.3 else ("Negative" if val < -0.3 else "Neutral")
            else:
                phase = "Warm" if val > 0.2 else ("Cool" if val < -0.2 else "Neutral")
            return {"value": round(val, 3), "phase": phase, "label": label, "description": desc}

        from datetime import datetime
        return {
            "enso":       _signal(idx["enso"], "ENSO",         "El Niño–Southern Oscillation (Niño 3.4)"),
            "iod":        _signal(idx["iod"],  "IOD",          "Indian Ocean Dipole"),
            "pdo":        _signal(idx["pdo"],  "PDO",          "Pacific Decadal Oscillation"),
            "atl":        _signal(idx["atl"],  "Atlantic SST", "Atlantic 3 SST anomaly"),
            "amm_jan":    {"value": amm} if amm is not None else None,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        logger.exception("Failed to load signals")
        raise HTTPException(status_code=500, detail=str(e))


# ── Forecast ───────────────────────────────────────────────────────
@app.get("/forecast")
def get_forecast(
    region: str = Query(..., description="Region key, e.g. 'tigray'"),
    season: str = Query(..., description="'Kiremt' or 'Belg'"),
    lang:   str = Query("en", description="'en' or 'am'"),
):
    """Generate a probabilistic forecast for one region + season."""
    _validate_season(season)
    try:
        result = _fc.forecast(region, season)
        return _numpy_safe(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Forecast failed for %s/%s", region, season)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/forecast/zone")
def get_zone_forecast(
    zone:         str = Query(...),
    zone_display: str = Query(...),
    region:       str = Query(...),
    season:       str = Query(...),
    lang:         str = Query("en"),
):
    """Generate a forecast for a sub-regional zone."""
    _validate_season(season)
    try:
        result = _fc.forecast_zone(zone, zone_display, region, season)
        return _numpy_safe(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Zone forecast failed for %s/%s", zone, season)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/forecast/all")
def get_all_forecasts(
    season: str = Query(..., description="'Kiremt' or 'Belg'"),
):
    """Quick forecast for all 13 regions (for the risk map, no advisory)."""
    _validate_season(season)
    try:
        results = _get_all_forecasts(season)
        return [_numpy_safe(r) for r in results]
    except Exception as e:
        logger.exception("All-forecasts failed for season=%s", season)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/forecast/zones")
def get_region_zone_forecasts(
    region: str = Query(...),
    season: str = Query(...),
):
    """All zone forecasts for a single region."""
    _validate_season(season)
    try:
        zones = _fc.get_zones_for_region(region)
        results = []
        for zone in zones:
            try:
                # get_zones_for_region() returns {zone_key, zone_display} (not {key, display})
                zk = zone["zone_key"]
                zd = zone["zone_display"]
                result = _fc.forecast_zone(zk, zd, region, season, fast=True)
                # Ensure zone_key / zone_display are present in the response
                result.setdefault("zone_key", zk)
                result.setdefault("zone_display", zd)
                results.append(_numpy_safe(result))
            except Exception as ze:
                logger.warning("Zone forecast failed for %s: %s", zone, ze)
        return results
    except Exception as e:
        logger.exception("Zone forecasts failed for %s/%s", region, season)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/zones")
def list_zones(
    region: str = Query(..., description="Region key, e.g. 'amhara'"),
):
    """List zones (sub-regions) for a given region — lightweight, no forecasts."""
    try:
        zones = _fc.get_zones_for_region(region)
        # Normalise to {zone_key, zone_display} regardless of internal format
        return [
            {
                "zone_key":     z.get("zone_key", z.get("key", "")),
                "zone_display": z.get("zone_display", z.get("display", "")),
            }
            for z in zones
        ]
    except Exception as e:
        logger.exception("Zone list failed for region=%s", region)
        raise HTTPException(status_code=500, detail=str(e))


# ── CHIRPS anomaly ────────────────────────────────────────────────
@app.get("/chirps-anomaly")
def get_chirps_anomaly(
    region: str = Query(...),
    season: str = Query(...),
):
    """Observed rainfall anomaly vs 1991–2020 baseline (CHIRPS)."""
    try:
        result = _get_season_anomaly(region, season)
        if result is None:
            return None
        # Normalise field names to match frontend types
        return {
            "region":       region,
            "season":       season,
            "anomaly_pct":  result.get("anomaly_pct"),
            "anomaly_mm":   result.get("total_mm"),
            "tercile":      result.get("status"),     # "Above Normal" / etc.
            "z_score":      result.get("z_score"),
            "completed":    result.get("completed"),
            "label":        result.get("label"),
        }
    except Exception as e:
        logger.exception("CHIRPS anomaly failed for %s/%s", region, season)
        raise HTTPException(status_code=500, detail=str(e))


# ── Market prices ─────────────────────────────────────────────────

def _parse_pct_change(trend_str: str) -> "float | None":
    """Extract numeric % change from strings like '+8% vs last month'."""
    import re
    m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%", trend_str or "")
    return float(m.group(1)) if m else None


def _normalize_price_row(raw: dict) -> dict:
    """Map raw forecaster.get_food_prices() fields to frontend CropPriceRow shape."""
    return {
        "commodity":        raw.get("crop", ""),
        "price_etb":        raw.get("price_etb"),
        "unit":             raw.get("unit", "per quintal (100kg)"),
        "date":             raw.get("date", ""),
        "price_change_pct": _parse_pct_change(raw.get("trend_str", "")),
        "trend_label":      raw.get("trend_str", ""),
        "market_name":      raw.get("region", ""),
        "is_regional":      raw.get("is_regional", False),
    }


@app.get("/prices")
def get_prices(region: str = Query(...)):
    """WFP market prices for key crops in a region (normalised for frontend)."""
    try:
        result = _fc.get_food_prices(region)
        if not result:
            return []
        rows = result if isinstance(result, list) else [result]
        return [_numpy_safe(_normalize_price_row(r)) for r in rows]
    except Exception as e:
        logger.exception("Prices failed for %s", region)
        raise HTTPException(status_code=500, detail=str(e))


# ── Regions ───────────────────────────────────────────────────────
@app.get("/regions")
def get_regions():
    """All supported regions with display names."""
    REGION_DISPLAY = {
        "addis_ababa":      "Addis Ababa",
        "afar":             "Afar",
        "amhara":           "Amhara",
        "benishangul_gumz": "Benishangul-Gumz",
        "dire_dawa":        "Dire Dawa",
        "gambela":          "Gambela",
        "harari":           "Harari",
        "oromia":           "Oromia",
        "sidama":           "Sidama",
        "snnpr":            "SNNPR",
        "somali":           "Somali",
        "south_west":       "South West",
        "tigray":           "Tigray",
    }
    return {
        "regions": [
            {"key": k, "display": v} for k, v in REGION_DISPLAY.items()
        ]
    }


# ── Validation ─────────────────────────────────────────────────────
@app.get("/validation/summary")
def get_validation_summary(season: str = Query(...)):
    """Aggregate validation metrics for one season."""
    _validate_season(season)
    try:
        import pandas as pd
        results_path = os.path.join(BASE_DIR, "data", "validation_results.csv")
        df = pd.read_csv(results_path)
        df = df[df["season"] == season]

        if df.empty:
            raise HTTPException(status_code=404, detail=f"No validation data for season '{season}'")

        from forecaster import KIREMT_RO_HSS, BELG_RO_HSS
        ro_lookup = KIREMT_RO_HSS if season == "Kiremt" else BELG_RO_HSS

        hss, _ = _compute_hss(df["actual"], df["predicted"])

        # LOOCV is in-sample; rolling-origin is the operative metric
        loocv_hss = float(hss)
        ro_hss_vals = [v for v in ro_lookup.values() if v is not None]
        ro_hss = float(np.mean(ro_hss_vals)) if ro_hss_vals else 0.0

        tiers = [_fc.get_release_tier(r, season) for r in ro_lookup.keys()]
        return {
            "season":        season,
            "aggregate_hss": round(ro_hss, 4),
            "loocv_hss":     round(loocv_hss, 4),
            "n_regions":     len(ro_lookup),
            "n_full":        tiers.count("full"),
            "n_experimental":tiers.count("experimental"),
            "n_suppressed":  tiers.count("suppressed"),
            "n_test_years":  int(df["year"].nunique()),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Validation summary failed for %s", season)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/validation/release-matrix")
def get_release_matrix(season: str = Query(...)):
    """Per-region rolling-origin HSS and release tier."""
    _validate_season(season)
    try:
        from forecaster import KIREMT_RO_HSS, BELG_RO_HSS
        import pandas as pd

        ro_lookup = KIREMT_RO_HSS if season == "Kiremt" else BELG_RO_HSS

        results_path = os.path.join(BASE_DIR, "data", "validation_results.csv")
        df = pd.read_csv(results_path)
        df = df[df["season"] == season]

        REGION_DISPLAY = {
            "addis_ababa":      "Addis Ababa", "afar":             "Afar",
            "amhara":           "Amhara",      "benishangul_gumz": "Benishangul-Gumz",
            "dire_dawa":        "Dire Dawa",   "gambela":          "Gambela",
            "harari":           "Harari",      "oromia":           "Oromia",
            "sidama":           "Sidama",      "snnpr":            "SNNPR",
            "somali":           "Somali",      "south_west":       "South West",
            "tigray":           "Tigray",
        }

        # _compute_hss is defined at module level (inlined from validation.py)
        rows = []
        for region_key, ro_hss in sorted(ro_lookup.items(), key=lambda x: -x[1]):
            region_df = df[df["region"] == region_key]
            cv_hss = None
            if not region_df.empty:
                try:
                    cv_hss_val, _ = _compute_hss(region_df["actual"], region_df["predicted"])
                    cv_hss = round(float(cv_hss_val), 4)
                except Exception:
                    pass
            rows.append({
                "region_key":     region_key,
                "region_display": REGION_DISPLAY.get(region_key, region_key),
                "ro_hss":         round(ro_hss, 4),
                "cv_hss":         cv_hss,
                "tier":           _fc.get_release_tier(region_key, season),
                "n_test_years":   int(region_df["year"].nunique()) if not region_df.empty else 0,
            })
        return rows
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Release matrix failed for %s", season)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/validation/timeline")
def get_validation_timeline(
    region: str = Query(...),
    season: str = Query(...),
):
    """Year-by-year rolling-origin predictions vs actuals for one region."""
    _validate_season(season)
    try:
        import pandas as pd
        results_path = os.path.join(BASE_DIR, "data", "validation_results.csv")
        df = pd.read_csv(results_path)
        df = df[(df["region"] == region) & (df["season"] == season)]
        df = df.sort_values("year")

        LABEL_MAP = {0: "Below Normal", 1: "Near Normal", 2: "Above Normal"}

        rows = []
        for _, row in df.iterrows():
            rows.append({
                "year":       int(row["year"]),
                "actual":     LABEL_MAP.get(int(row["actual"]),    str(row["actual"])),
                "predicted":  LABEL_MAP.get(int(row["predicted"]), str(row["predicted"])),
                "correct":    bool(row["correct"]),
                "prob_below": float(row.get("prob_below", 0)),
                "prob_near":  float(row.get("prob_near",  0)),
                "prob_above": float(row.get("prob_above", 0)),
            })
        return rows
    except Exception as e:
        logger.exception("Timeline failed for %s/%s", region, season)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/validation/reliability")
def get_validation_reliability(
    region: str = Query(...),
    season: str = Query(...),
):
    """Reliability diagram data (forecast probability vs observed frequency)."""
    _validate_season(season)
    try:
        import pandas as pd
        results_path = os.path.join(BASE_DIR, "data", "validation_results.csv")
        df = pd.read_csv(results_path)
        df = df[(df["region"] == region) & (df["season"] == season)]

        # Bin forecast probabilities and compute observed frequency per bin
        bins = [0.0, 0.2, 0.35, 0.5, 0.65, 0.8, 1.01]
        rows = []

        for col, label_val in [
            ("prob_below", 0), ("prob_near", 1), ("prob_above", 2)
        ]:
            if col not in df.columns:
                continue
            for i in range(len(bins) - 1):
                mask = (df[col] >= bins[i]) & (df[col] < bins[i + 1])
                sub  = df[mask]
                if sub.empty:
                    continue
                obs_freq = (sub["actual"] == label_val).mean()
                rows.append({
                    "class":        label_val,
                    "forecast_prob": round((bins[i] + bins[i + 1]) / 2, 3),
                    "observed_freq": round(float(obs_freq), 3),
                    "n":             int(len(sub)),
                })
        return rows
    except Exception as e:
        logger.exception("Reliability failed for %s/%s", region, season)
        raise HTTPException(status_code=500, detail=str(e))


# ── Dev entrypoint ────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True,
                reload_dirs=[SRC_DIR, os.path.join(BASE_DIR, "api")])
