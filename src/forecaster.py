"""
Azmera — Forecast Engine
Takes current climate indices → outputs seasonal forecast + advisory
"""

import pandas as pd
import numpy as np
import pickle
import os
import time
import requests

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "../models")
DATA_DIR   = os.path.join(BASE_DIR, "../data/raw")
ZONE_MODELS_DIR = os.path.join(BASE_DIR, "../models/zones")

# Minimum CV HSS to show a zone forecast (below this = fall back to region)
# 49/156 zone models have HSS <= 0 (worse than random) — those fall back to region model
ZONE_CV_THRESHOLD = 0.0  # HSS > 0 required; enforced via cv_hss (new) or cv_accuracy (legacy)

# Legacy threshold kept for reference — no_skill now driven by rolling-origin release tier.
REGION_SKILL_THRESHOLD = 0.0

# ── Release matrix — rolling-origin HSS by region-season ──────────────────────
# Source: scripts/validate_rolling_origin.py
#   Kiremt: Phase D (region-specific lean ± antecedent features)
#   Belg:   Phase F (region-specific lean ± AMM Jan features)
#   Protocol: train on 1981..T−1, forecast T, advancing T from 1995→2021
#   Coverage: 27 rolling-origin test years × 13 regions = 351 pairs per season
#
# Rolling-origin is the OPERATIONAL skill metric. LOOCV overstates skill because
# each held-out year is tested against a model trained on future years. Rolling-origin
# uses only past data to forecast each year — the honest prospective benchmark.
#
# Release tier thresholds (rolling-origin HSS):
#   'full'         RO_HSS ≥ +0.10  — meaningful prospective skill demonstrated
#   'experimental' 0.0 < RO_HSS < +0.10 — positive but marginal; show with warning
#   'suppressed'   RO_HSS ≤ 0.0   — no prospective skill; issuing forecast misleads users

KIREMT_RO_HSS: dict = {
    # Phase D rolling-origin results (hss_d column, validate_rolling_origin.py)
    "addis_ababa":      -0.049,  # suppressed — rolling-origin negative despite +0.039 LOOCV
    "afar":             +0.071,  # experimental
    "amhara":           +0.044,  # experimental
    "benishangul_gumz": +0.471,  # full — WMO-grade (>0.3), strongest signal in dataset
    "dire_dawa":        +0.024,  # experimental
    "gambela":          +0.012,  # experimental — positive despite −0.013 LOOCV
    "harari":           +0.102,  # full — uses dire_dawa model (pixel-identical CHIRPS)
    "oromia":           -0.111,  # suppressed — large negative despite +0.227 LOOCV
    "sidama":           -0.130,  # suppressed
    "snnpr":            +0.077,  # experimental — positive despite −0.005 LOOCV
    "somali":           +0.206,  # full
    "south_west":       +0.025,  # experimental
    "tigray":           +0.106,  # full
}

BELG_RO_HSS: dict = {
    # Phase F rolling-origin results (hss_phase_f column, validate_rolling_origin.py)
    # BELG_AMM_INCLUDE regions use lean + amm_sst_jan; others use lean baseline.
    "addis_ababa":      +0.111,  # full (AMM2 choice, Δ+0.143 vs baseline)
    "afar":             +0.046,  # experimental (baseline choice)
    "amhara":           +0.199,  # full (baseline choice)
    "benishangul_gumz": +0.056,  # experimental (AMM2 choice, Δ+0.006 vs baseline)
    "dire_dawa":        +0.096,  # experimental (AMM2 choice, Δ+0.117 vs baseline)
    "gambela":          +0.147,  # full (AMM2 choice, Δ+0.214 vs baseline)
    "harari":           +0.096,  # experimental — uses dire_dawa model (same CHIRPS pixel)
    "oromia":           -0.084,  # suppressed (AMM2 best choice but still negative)
    "sidama":           -0.025,  # suppressed (baseline choice)
    "snnpr":            -0.101,  # suppressed (baseline choice)
    "somali":           +0.100,  # full (baseline choice)
    "south_west":       +0.160,  # full (baseline choice)
    "tigray":           +0.032,  # experimental (AMM2 choice, Δ+0.123 vs baseline)
}

RO_FULL_THRESHOLD     = 0.10   # rolling-origin HSS ≥ this → 'full'
RO_SUPPRESS_THRESHOLD = 0.00   # rolling-origin HSS ≤ this → 'suppressed'


def get_release_tier(region_key: str, season_key: str) -> str:
    """Return the release tier for a region-season based on rolling-origin validation.

    Tiers
    -----
    'full'         rolling-origin HSS ≥ 0.10  — meaningful prospective skill
    'experimental' rolling-origin HSS in (0, 0.10) — positive but marginal
    'suppressed'   rolling-origin HSS ≤ 0.0   — no prospective skill demonstrated

    OND and Bega always return 'suppressed' (no validated seasonal model).
    Unknown regions default to 'experimental' (conservative fallback).
    """
    if season_key == "Kiremt":
        ro_hss = KIREMT_RO_HSS.get(region_key)
    elif season_key == "Belg":
        ro_hss = BELG_RO_HSS.get(region_key)
    else:
        return "suppressed"   # OND, Bega — no validated forecast

    if ro_hss is None:
        return "experimental"  # unknown region: conservative default

    if ro_hss >= RO_FULL_THRESHOLD:
        return "full"
    elif ro_hss > RO_SUPPRESS_THRESHOLD:
        return "experimental"
    else:
        return "suppressed"

# ── Load region model and encoder ─────────────────────────────────
def load_model():
    with open(os.path.join(MODELS_DIR, "azmera_model_v3.pkl"), "rb") as f:
        model = pickle.load(f)
    with open(os.path.join(MODELS_DIR, "region_encoder.pkl"), "rb") as f:
        le = pickle.load(f)
    with open(os.path.join(MODELS_DIR, "feature_cols.pkl"), "rb") as f:
        feature_cols = pickle.load(f)
    return model, le, feature_cols

# ── Load per-region model ─────────────────────────────────────────
_REGION_MODEL_CACHE = {}

def load_region_model(region_key, season_key):
    """Load a per-region model. Falls back to shared model if not found.

    Harari routes to the Dire Dawa model: confirmed 42/42 identical SPI and
    target values between Harari and Dire Dawa (same CHIRPS pixel). Training
    separate models on pixel-identical data is scientifically unjustified —
    the Dire Dawa model is used for both regions operationally.
    """
    # Route Harari to Dire Dawa (pixel-identical CHIRPS extraction confirmed)
    effective_key = "dire_dawa" if region_key == "harari" else region_key
    cache_key = f"{effective_key}_{season_key.lower()}"
    if cache_key in _REGION_MODEL_CACHE:
        return _REGION_MODEL_CACHE[cache_key]
    path = os.path.join(BASE_DIR, f"../models/regions/{cache_key}.pkl")
    if not os.path.exists(path):
        _REGION_MODEL_CACHE[cache_key] = None
        return None
    with open(path, "rb") as f:
        data = pickle.load(f)
    _REGION_MODEL_CACHE[cache_key] = data
    return data

# ── Load zone model ───────────────────────────────────────────────
_ZONE_MODEL_CACHE = {}

def load_zone_model(zone_key, season_key):
    """Load a zone-level model. Cached in memory after first load."""
    cache_key = f"{zone_key}_{season_key.lower()}"
    if cache_key in _ZONE_MODEL_CACHE:
        return _ZONE_MODEL_CACHE[cache_key]
    path = os.path.join(ZONE_MODELS_DIR, f"{cache_key}.pkl")
    if not os.path.exists(path):
        _ZONE_MODEL_CACHE[cache_key] = None
        return None
    with open(path, "rb") as f:
        model = pickle.load(f)
    _ZONE_MODEL_CACHE[cache_key] = model
    return model

# ── Load zone centroids ───────────────────────────────────────────
def load_zone_centroids():
    path = os.path.join(BASE_DIR, "../data/zone_centroids.csv")
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        print(f"[Azmera] WARNING: zone_centroids.csv not found at {path}. Zone drilling will be unavailable.")
        return pd.DataFrame(columns=["zone_key", "zone_display", "region_key", "lat", "lon"])
    except Exception as e:
        print(f"[Azmera] WARNING: Could not load zone_centroids.csv: {e}")
        return pd.DataFrame(columns=["zone_key", "zone_display", "region_key", "lat", "lon"])

# ── Get zones for a region ────────────────────────────────────────
def get_zones_for_region(region_key):
    """Return list of zones for a given region key."""
    centroids = load_zone_centroids()

    REGION_KEY_MAP = {
        "oromia":             "oromia",
        "amhara":             "amhara",
        "tigray":             "tigray",
        "snnpr":              "southernnationsnationalities",
        "sidama":             "southernnationsnationalities",
        "south_west":         "southernnationsnationalities",
        "afar":               "afar",
        "somali":             "somali",
        "gambela":            "gambelapeoples",
        "benishangul_gumz":   "benshangul_gumaz",
        "addis_ababa":        "addisabeba",
        "dire_dawa":          "diredawa",
        "harari":             "hararipeople",
    }

    centroid_region = REGION_KEY_MAP.get(region_key, region_key)
    zones = centroids[centroids["region_key"] == centroid_region]
    return zones[["zone_key", "zone_display"]].to_dict("records")

# ── Load latest climate indices ───────────────────────────────────
_INDICES_CACHE = None
_INDICES_CACHE_LOADED_AT = 0.0
_INDICES_CACHE_TTL = 3600  # seconds — matches @st.cache_data(ttl=3600) in app.py

# ── AMM Jan index cache ───────────────────────────────────────────
# Phase F Belg feature: amm_sst_jan = January AMM of the forecast year.
# Published ~Feb 15 → safe for late-February Belg issuance.
_AMM_JAN_CACHE = None
_AMM_JAN_LOADED_AT = 0.0
_AMM_JAN_TTL = 3600  # 1 hour — same as indices cache TTL

def get_latest_indices():
    """
    Load most recent ENSO, IOD, PDO, Atlantic SST values.
    In-process cache with 1-hour TTL — respects the same window as Streamlit's cache_data.
    """
    global _INDICES_CACHE, _INDICES_CACHE_LOADED_AT
    if _INDICES_CACHE is not None and (time.time() - _INDICES_CACHE_LOADED_AT) < _INDICES_CACHE_TTL:
        return _INDICES_CACHE
    enso = pd.read_csv(os.path.join(DATA_DIR, "enso_index.csv"),
                       parse_dates=["date"]).sort_values("date")
    iod  = pd.read_csv(os.path.join(DATA_DIR, "iod_index.csv"),
                       parse_dates=["date"]).sort_values("date")
    pdo  = pd.read_csv(os.path.join(DATA_DIR, "pdo_index.csv"),
                       parse_dates=["date"]).sort_values("date")
    atl  = pd.read_csv(os.path.join(DATA_DIR, "atlantic_sst.csv"),
                       parse_dates=["date"]).sort_values("date")

    iod  = iod[iod["iod"]  > -999]
    pdo  = pdo[pdo["pdo"]  > -9.0]
    enso = enso[enso["enso"].notna()]
    atl  = atl[atl["atlantic_sst"].notna()]

    def last3(df, col):
        return df[col].dropna().tail(3).values

    _INDICES_CACHE = {
        "enso": last3(enso, "enso"),
        "iod":  last3(iod,  "iod"),
        "pdo":  last3(pdo,  "pdo"),
        "atl":  last3(atl,  "atlantic_sst"),
    }
    _INDICES_CACHE_LOADED_AT = time.time()
    return _INDICES_CACHE

def get_latest_amm_jan():
    """
    Return the most recent January AMM SST value from data/raw/amm_index.csv.

    For Belg forecast issued late February, January of the current year is the
    operationally safe lag (published ~Feb 15 ✓).  Falls back to 0.0
    (climatological neutral) if file is missing or no valid January is found.

    Used by Phase F Belg models in BELG_AMM_INCLUDE regions.
    """
    global _AMM_JAN_CACHE, _AMM_JAN_LOADED_AT
    if (_AMM_JAN_CACHE is not None and
            (time.time() - _AMM_JAN_LOADED_AT) < _AMM_JAN_TTL):
        return _AMM_JAN_CACHE

    amm_path = os.path.join(DATA_DIR, "amm_index.csv")
    if not os.path.exists(amm_path):
        print(f"[Azmera] WARNING: amm_index.csv not found at {amm_path}. "
              "Using 0.0 fallback for amm_sst_jan.")
        _AMM_JAN_CACHE = 0.0
        _AMM_JAN_LOADED_AT = time.time()
        return _AMM_JAN_CACHE

    try:
        amm = pd.read_csv(amm_path, parse_dates=["date"])
        amm = amm[amm["amm_sst"].notna()]
        jan_rows = amm[amm["date"].dt.month == 1].sort_values("date")
        if jan_rows.empty:
            print("[Azmera] WARNING: No valid January AMM values found. Using 0.0.")
            _AMM_JAN_CACHE = 0.0
        else:
            _AMM_JAN_CACHE = float(jan_rows.iloc[-1]["amm_sst"])
    except Exception as e:
        print(f"[Azmera] WARNING: Failed to load amm_index.csv: {e}. Using 0.0.")
        _AMM_JAN_CACHE = 0.0

    _AMM_JAN_LOADED_AT = time.time()
    return _AMM_JAN_CACHE


def get_food_prices(region):
    """
    Pull latest WFP food prices for a given Ethiopian region from HDX.
    No API key needed — completely free and public.
    """
    import io

    HDX_URL = (
        "https://data.humdata.org/dataset/2e4f1922-e446-4b57-a98a-"
        "d0e2d5e34afa/resource/87bac18e-f3aa-4b29-8cf8-"
        "76763e823dc5/download"
    )

    REGION_MAP = {
        "oromia":           "Oromia",
        "amhara":           "Amhara",
        "tigray":           "Tigray",
        "snnpr":            "SNNPR",
        "afar":             "Afar",
        "somali":           "Somali",
        "gambela":          "Gambela",
        "benishangul_gumz": "B. Gumuz",
        "addis_ababa":      "Addis Ababa",
        "dire_dawa":        "Dire Dawa",
        "harari":           "Harari",
        "sidama":           "SNNPR",
        "south_west":       "SNNPR",
    }

    KEY_CROPS = [
        "Teff", "Teff (white)", "Teff (mixed)",
        "Maize", "Maize (white)",
        "Sorghum", "Sorghum (white)", "Sorghum (mixed)",
        "Wheat", "Wheat (mixed)",
        "Barley",
    ]

    CROP_LABELS = {
        "Teff":            "Teff",
        "Teff (white)":    "Teff (white)",
        "Teff (mixed)":    "Teff",
        "Maize":           "Maize (Bekolo)",
        "Maize (white)":   "Maize (Bekolo)",
        "Sorghum":         "Sorghum (Mashilla)",
        "Sorghum (white)": "Sorghum (Mashilla)",
        "Sorghum (mixed)": "Sorghum (Mashilla)",
        "Wheat":           "Wheat (Sinde)",
        "Wheat (mixed)":   "Wheat (Sinde)",
        "Barley":          "Barley (Gabs)",
    }

    try:
        r = requests.get(HDX_URL, timeout=30)
        r.raise_for_status()

        df = pd.read_csv(io.StringIO(r.text))
        df["date"] = pd.to_datetime(df["date"])

        hdx_region = REGION_MAP.get(region.lower(), "Oromia")
        region_df  = df[
            (df["admin1"] == hdx_region) &
            (df["commodity"].isin(KEY_CROPS))
        ].copy()

        region_df = region_df[region_df["price"] >= 100]

        is_regional = not region_df.empty
        if region_df.empty:
            region_df = df[
                (df["commodity"].isin(KEY_CROPS)) &
                (df["price"] >= 100)
            ].copy()

        latest_date = region_df["date"].max()
        this_month  = latest_date - pd.DateOffset(months=1)
        last_month  = latest_date - pd.DateOffset(months=2)

        recent = (
            region_df[region_df["date"] >= this_month]
            .groupby("commodity")["price"]
            .mean()
            .reset_index()
            .rename(columns={"price": "price_recent"})
        )

        prev = (
            region_df[
                (region_df["date"] >= last_month) &
                (region_df["date"] <  this_month)
            ]
            .groupby("commodity")["price"]
            .mean()
            .reset_index()
            .rename(columns={"price": "price_prev_month"})
        )

        latest = recent.merge(prev, on="commodity", how="left")
        latest["price_etb"] = latest["price_recent"]
        latest["pct_change"] = (
            (latest["price_recent"] - latest["price_prev_month"])
            / latest["price_prev_month"] * 100
        )
        latest["label"]    = latest["commodity"].map(CROP_LABELS)
        latest["date_str"] = latest_date.strftime("%b %Y")

        results    = []
        seen_labels = set()

        for _, row in latest.iterrows():
            label = row["label"]
            if label in seen_labels or pd.isna(label):
                continue
            seen_labels.add(label)

            pct = row["pct_change"]

            if pd.isna(pct):
                trend     = "⚪"
                trend_str = "No comparison data"
            elif pct > 10:
                trend     = "🔴"
                trend_str = f"+{pct:.0f}% vs last month"
            elif pct > 3:
                trend     = "🟠"
                trend_str = f"+{pct:.0f}% vs last month"
            elif pct < -3:
                trend     = "🟢"
                trend_str = f"{pct:.0f}% vs last month"
            else:
                trend     = "⚪"
                trend_str = f"{pct:+.0f}% vs last month"

            results.append({
                "crop":        label,
                "price_etb":   row["price_etb"],
                "unit":        "per quintal (100kg)",
                "date":        row["date_str"],
                "trend":       trend,
                "trend_str":   trend_str,
                "region":      hdx_region,
                "is_regional": is_regional,
            })

        return results[:5]

    except Exception as e:
        print(f"Food prices error: {e}")
        return []

# ── Build feature vector (region model) ───────────────────────────
def build_features(region, season, indices, le):
    """Build the 19-feature vector for a given region and season."""

    enso3 = indices["enso"]
    iod3  = indices["iod"]
    pdo3  = indices["pdo"]
    atl3  = indices["atl"]

    def safe_get(arr, i):
        try: return float(arr[-(i)])
        except: return 0.0

    features = {
        "enso_lag1":        safe_get(enso3, 1),
        "iod_lag1":         safe_get(iod3,  1),
        "enso_lag2":        safe_get(enso3, 2),
        "iod_lag2":         safe_get(iod3,  2),
        "enso_lag3":        safe_get(enso3, 3),
        "iod_lag3":         safe_get(iod3,  3),
        "enso_3mo_mean":    float(np.mean(enso3)),
        "iod_3mo_mean":     float(np.mean(iod3)),
        "pdo_lag1":         safe_get(pdo3,  1),
        "pdo_lag2":         safe_get(pdo3,  2),
        "pdo_lag3":         safe_get(pdo3,  3),
        "pdo_3mo_mean":     float(np.mean(pdo3)),
        "atlantic_lag1":    safe_get(atl3,  1),
        "atlantic_lag2":    safe_get(atl3,  2),
        "atlantic_lag3":    safe_get(atl3,  3),
        "atlantic_3mo_mean":float(np.mean(atl3)),
        "spi_lag3":         0.0,
        "region_encoded":   int(le.transform([region.lower()])[0]),
        "is_kiremt":        1 if season == "Kiremt" else 0,
    }

    return pd.DataFrame([features])

# ── Build feature vector (zone model) ────────────────────────────
def build_zone_features(indices, spi_lag1=0.0):
    """Build feature vector for zone model (no region encoding needed)."""
    enso3 = indices["enso"]
    iod3  = indices["iod"]
    pdo3  = indices["pdo"]
    atl3  = indices["atl"]

    def safe_get(arr, i):
        try: return float(arr[-(i)])
        except: return 0.0

    return {
        "enso_lag1":         safe_get(enso3, 1),
        "enso_lag2":         safe_get(enso3, 2),
        "enso_lag3":         safe_get(enso3, 3),
        "enso_3mo_mean":     float(np.mean(enso3)),
        "iod_lag1":          safe_get(iod3,  1),
        "iod_lag2":          safe_get(iod3,  2),
        "iod_lag3":          safe_get(iod3,  3),
        "iod_3mo_mean":      float(np.mean(iod3)),
        "pdo_lag1":          safe_get(pdo3,  1),
        "pdo_lag2":          safe_get(pdo3,  2),
        "pdo_lag3":          safe_get(pdo3,  3),
        "pdo_3mo_mean":      float(np.mean(pdo3)),
        "atlantic_lag1":     safe_get(atl3,  1),
        "atlantic_lag2":     safe_get(atl3,  2),
        "atlantic_lag3":     safe_get(atl3,  3),
        "atlantic_3mo_mean": float(np.mean(atl3)),
        "spi_lag1":          spi_lag1,
    }

# ── Main region forecast function ─────────────────────────────────
def forecast(region, season, fast=False):
    """
    Generate seasonal rainfall forecast for a region.
    Uses per-region model if available, falls back to shared model.
    Only Kiremt and Belg are supported — OND/Bega raise ValueError.
    """
    if season not in ("Kiremt", "Belg"):
        raise ValueError(f"Season '{season}' not supported. Only Kiremt and Belg have validated forecast skill.")

    indices   = get_latest_indices()
    label_map = {0: "Below Normal", 1: "Near Normal", 2: "Above Normal"}

    region_data = load_region_model(region, season)

    if region_data is not None:
        # Use per-region model — captures region-specific climate relationships
        model        = region_data["model"]
        feature_cols = region_data["feature_cols"]

        # Build feature dict matching training features (no region encoding needed)
        enso3 = indices["enso"]
        iod3  = indices["iod"]
        pdo3  = indices["pdo"]
        atl3  = indices["atl"]
        def safe_get(arr, i):
            try: return float(arr[-(i)])
            except: return 0.0

        features = {
            "enso_lag1":         safe_get(enso3, 1),
            "enso_lag2":         safe_get(enso3, 2),
            "enso_lag3":         safe_get(enso3, 3),
            "enso_3mo_mean":     float(np.mean(enso3)),
            "iod_lag1":          safe_get(iod3,  1),
            "iod_lag2":          safe_get(iod3,  2),
            "iod_lag3":          safe_get(iod3,  3),
            "iod_3mo_mean":      float(np.mean(iod3)),
            "pdo_lag1":          safe_get(pdo3,  1),
            "pdo_lag2":          safe_get(pdo3,  2),
            "pdo_lag3":          safe_get(pdo3,  3),
            "pdo_3mo_mean":      float(np.mean(pdo3)),
            "atlantic_lag1":     safe_get(atl3,  1),
            "atlantic_lag2":     safe_get(atl3,  2),
            "atlantic_lag3":     safe_get(atl3,  3),
            "atlantic_3mo_mean": float(np.mean(atl3)),
            # belg_antecedent_anom_z: Phase C/D feature for Kiremt models.
            # Populated below from CHIRPS if the model requires it; 0.0 otherwise.
            "belg_antecedent_anom_z": 0.0,
            # amm_sst_jan: Phase F feature for Belg models in BELG_AMM_INCLUDE regions.
            # Populated below from amm_index.csv if the model requires it; 0.0 otherwise.
            # For Belg regions NOT in BELG_AMM_INCLUDE, this key is not in feature_cols
            # and is silently filtered out by X = pd.DataFrame([features])[feature_cols].
            "amm_sst_jan": 0.0,
        }

        # Populate Belg antecedent only if the per-region model was trained with it.
        # Try/except guards against test environments where rasterio may not be
        # installed; in production the conda env always has rasterio available.
        # On any failure, the pre-set 0.0 fallback (neutral) is used.
        if "belg_antecedent_anom_z" in feature_cols:
            try:
                from chirps_anomaly import get_region_belg_antecedent_anom_z
                features["belg_antecedent_anom_z"] = get_region_belg_antecedent_anom_z(
                    region, season
                )
            except Exception:
                pass  # fallback 0.0 already set above

        # Populate AMM Jan only if the per-region Belg model was trained with it.
        # Phase F: 7 Belg regions in BELG_AMM_INCLUDE use amm_sst_jan.
        # get_latest_amm_jan() reads data/raw/amm_index.csv with a 1-hour TTL cache.
        # On any failure, the pre-set 0.0 fallback (neutral) is used.
        if "amm_sst_jan" in feature_cols:
            try:
                features["amm_sst_jan"] = get_latest_amm_jan()
            except Exception:
                pass  # fallback 0.0 already set above

        X = pd.DataFrame([features])[feature_cols]
        probs      = model.predict_proba(X)[0]
        pred       = model.predict(X)[0]
        source     = "region_model"
        cv_accuracy = region_data["metrics"]["cv_accuracy"]
        cv_hss      = region_data["metrics"].get("cv_hss", None)
    else:
        # Fall back to shared model
        model, le, feature_cols = load_model()
        X = build_features(region, season, indices, le)
        X = X[feature_cols]
        probs      = model.predict_proba(X)[0]
        pred       = model.predict(X)[0]
        source     = "shared_model"
        cv_accuracy = None
        cv_hss      = None

    confidence = float(probs.max())
    prediction = label_map[pred]

    _enso_arr = indices.get("enso", [])
    if len(_enso_arr) == 0:
        print(f"[Azmera] WARNING: ENSO index array is empty for {region}/{season}. Defaulting to 0.0.")
    enso_val = float(_enso_arr[-1]) if len(_enso_arr) > 0 else 0.0
    enso_str = "El Niño" if enso_val > 0.5 else \
               "La Niña" if enso_val < -0.5 else "Neutral"

    # Determine release tier from rolling-origin validation (prospective skill metric).
    # NOTE: `region` (not `effective_key`) is used — KIREMT/BELG_RO_HSS contains a
    # dedicated harari row that reflects the dire_dawa model's rolling-origin results.
    release_tier = get_release_tier(region, season)
    ro_lookup    = KIREMT_RO_HSS if season == "Kiremt" else BELG_RO_HSS
    ro_hss_val   = ro_lookup.get(region)

    # no_skill = suppressed tier: rolling-origin HSS ≤ 0 → no prospective skill.
    # UI will show "No Validated Forecast" panel and suppress the advisory.
    no_skill = (release_tier == "suppressed")

    result = {
        "region":        region,
        "season":        season,
        "prediction":    prediction,
        "confidence":    confidence,
        "prob_below":    float(probs[0]),
        "prob_near":     float(probs[1]),
        "prob_above":    float(probs[2]),
        "enso_current":  enso_val,
        "enso_phase":    enso_str,
        "source":        source,
        "cv_accuracy":   cv_accuracy,
        "cv_hss":        cv_hss,
        "release_tier":  release_tier,   # 'full' / 'experimental' / 'suppressed'
        "ro_hss":        ro_hss_val,     # rolling-origin HSS (None if not in lookup)
        "no_skill":      no_skill,       # True when rolling-origin HSS ≤ 0
    }
    if not fast:
        result["advisory_en"] = generate_advisory(
            region, season, prediction, confidence, enso_str, probs, "en",
            release_tier=release_tier, ro_hss=ro_hss_val)
        result["advisory_am"] = generate_advisory(
            region, season, prediction, confidence, enso_str, probs, "am",
            release_tier=release_tier, ro_hss=ro_hss_val)
    return result

# ── Zone forecast function ────────────────────────────────────────
def forecast_zone(zone_key, zone_display, region_key, season, fast=False):
    """
    Generate zone-level forecast. Falls back to region if CV < threshold.
    Only Kiremt and Belg are supported — OND/Bega raise ValueError.
    """
    if season not in ("Kiremt", "Belg"):
        raise ValueError(f"Season '{season}' not supported for zone forecasts.")

    indices = get_latest_indices()
    label_map = {0: "Below Normal", 1: "Near Normal", 2: "Above Normal"}

    zone_data = load_zone_model(zone_key, season)

    if zone_data is not None:
        cv_accuracy = zone_data["metrics"]["cv_accuracy"]
        cv_hss = zone_data["metrics"].get("cv_hss", None)

        # Use HSS for threshold if available (new models), else fall back to accuracy
        skill_score = cv_hss if cv_hss is not None else cv_accuracy
        if skill_score >= ZONE_CV_THRESHOLD:
            model        = zone_data["model"]
            feature_cols = zone_data["feature_cols"]

            # Use real spi_lag1 from previous season CHIRPS (not placeholder 0.0)
            from chirps_anomaly import get_zone_spi_lag1
            spi_lag1 = get_zone_spi_lag1(zone_key, season)
            features = build_zone_features(indices, spi_lag1=spi_lag1)
            X = pd.DataFrame([features])[feature_cols]

            probs      = model.predict_proba(X)[0]
            pred       = model.predict(X)[0]
            confidence = float(probs.max())
            prediction = label_map[pred]

            enso_val = float(indices["enso"][-1])
            enso_str = "El Niño" if enso_val > 0.5 else \
                       "La Niña" if enso_val < -0.5 else "Neutral"

            # Inherit region's release tier — no per-zone rolling-origin available.
            zone_release_tier = get_release_tier(region_key, season)
            zone_ro_lookup    = KIREMT_RO_HSS if season == "Kiremt" else BELG_RO_HSS
            zone_ro_hss       = zone_ro_lookup.get(region_key)

            result = {
                "zone":         zone_display,
                "zone_key":     zone_key,
                "region":       region_key,
                "season":       season,
                "prediction":   prediction,
                "confidence":   confidence,
                "prob_below":   float(probs[0]),
                "prob_near":    float(probs[1]),
                "prob_above":   float(probs[2]),
                "enso_current": enso_val,
                "enso_phase":   enso_str,
                "cv_accuracy":  cv_accuracy,
                "source":       "zone",
                "release_tier": zone_release_tier,
                "ro_hss":       zone_ro_hss,
                "no_skill":     (zone_release_tier == "suppressed"),
            }
            if not fast:
                result["advisory_en"] = generate_advisory(
                    zone_display, season, prediction,
                    confidence, enso_str, probs, "en",
                    release_tier=zone_release_tier, ro_hss=zone_ro_hss)
                result["advisory_am"] = generate_advisory(
                    zone_display, season, prediction,
                    confidence, enso_str, probs, "am",
                    release_tier=zone_release_tier, ro_hss=zone_ro_hss)
            return result
        else:
            result = forecast(region_key, season, fast=fast)
            result["zone"]        = zone_display
            result["zone_key"]    = zone_key
            result["source"]      = "region_fallback"
            result["cv_accuracy"] = cv_accuracy
            result["fallback_reason"] = f"Zone model skill too low ({cv_accuracy:.0%} CV)"
            return result
    else:
        result = forecast(region_key, season, fast=fast)
        result["zone"]        = zone_display
        result["zone_key"]    = zone_key
        result["source"]      = "region_fallback"
        result["cv_accuracy"] = None
        result["fallback_reason"] = "No zone model available"
        return result

# ── Advisory text generation ──────────────────────────────────────
def _advisory_fallback(region, season, prediction, probs, language):
    """
    Safe fallback advisory when OpenAI is unavailable.
    Honest, deterministic — does not invent climate facts.
    """
    label = prediction  # "Below Normal" / "Near Normal" / "Above Normal"
    pct_below = int(probs[0] * 100)
    pct_near  = int(probs[1] * 100)
    pct_above = int(probs[2] * 100)

    if language == "am":
        return (
            f"• 🌦️ ለ{region.title()} {season} ወቅት {label} ዝናብ ተተነበይቷል።\n"
            "• 🌱 ለዝርዝር የእርሻ ምክር እባክዎ የአካባቢ የግብርና ባለሙያዎችን ያነጋግሩ።\n"
            "• 💧 ከ ICPAC እና ከኢትዮጵያ ሜቴዎሮሎጂ ኢንስቲትዩት ኦፊሴላዊ ምክሮችን ይከተሉ።\n"
            "• 🌾 የ AI ምክር አሁን አይገኝም — እባክዎ ዳግም ይሞክሩ።"
        )
    return (
        f"• 🌦️ Forecast for {region.title()}: {label} rainfall during {season} season "
        f"({pct_below}% drought / {pct_near}% normal / {pct_above}% above normal).\n"
        "• 🌱 Consult your local agricultural extension officer for crop-specific advice "
        "tailored to your area and soil type.\n"
        "• 💧 Follow official seasonal advisories from ICPAC and Ethiopia's National "
        "Meteorological Institute (NMA) for water and irrigation guidance.\n"
        "• 🌾 AI-generated advisory temporarily unavailable — please try again later."
    )


def generate_advisory(region, season, prediction, confidence,
                      enso_phase, probs, language="en",
                      release_tier="full", ro_hss=None):
    """Generate farmer advisory using OpenAI. Falls back to deterministic text on any failure."""

    # client init is inside the try block so constructor failures are caught.
    # st.secrets takes precedence (Streamlit Cloud); fall back to .env / OS env var.
    try:
        import streamlit as st
        api_key = st.secrets.get("OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    except Exception:
        api_key = os.getenv("OPENAI_API_KEY", "")

    _SEASON_MONTHS_MAP = {
        "Kiremt": "June–September",
        "Belg":   "March–May",
        "OND":    "October–December",
        "Bega":   "January–February",
    }
    season_months = _SEASON_MONTHS_MAP.get(season, season)

    # Build tier-specific tone instruction for the prompt
    hss_str = f"{ro_hss:+.3f}" if ro_hss is not None else "unknown"
    if release_tier == "experimental":
        tier_instruction = (
            f"IMPORTANT: This is an EXPERIMENTAL forecast with limited demonstrated skill "
            f"(rolling-origin HSS = {hss_str}). The model has shown some positive skill "
            f"in hindcasts but not enough to be fully validated. You MUST use cautious, "
            f"conditional language throughout. Use phrases like 'if the forecast is correct', "
            f"'consider as one input among many', 'consult local extension officers before acting'. "
            f"Avoid strong directives. Replace 'plant X' with 'consider planting X'. "
            f"Acknowledge uncertainty explicitly in at least two bullets."
        )
    else:
        tier_instruction = (
            "This is a FULL validated forecast. You may use clear, practical language."
        )

    prompt = f"""
    You are an expert agricultural advisor specializing in Ethiopian smallholder farming.
    Generate a seasonal forecast advisory with specific crop recommendations.

    Forecast details:
    - Region: {region.title()}
    - Season: {season} ({season_months})
    - Prediction: {prediction} rainfall
    - Confidence: {confidence:.0%}
    - ENSO Phase: {enso_phase}
    - Drought probability: {probs[0]:.0%}
    - Normal probability:  {probs[1]:.0%}
    - Above normal probability: {probs[2]:.0%}
    - Forecast tier: {release_tier} (RO-HSS = {hss_str})

    Tone guidance: {tier_instruction}

    Ethiopian crops to consider recommending based on conditions:

    DROUGHT/DRY CONDITIONS — recommend these:
    - Sorghum (Mashilla) — extremely drought tolerant, widely grown in Ethiopia
    - Teff (Eragrostis tef) — Ethiopia's staple grain, moderate drought tolerance
    - Chickpea (Shimbra) — good for drier Belg season, nitrogen fixing
    - Faba Bean (Ater) — tolerates dry spells, important protein source
    - Finger Millet (Dagusa) — very drought hardy, grown in Tigray/SNNPR
    - Groundnut — drought tolerant, good for Afar/Somali lowlands
    - Sesame (Selit) — extremely drought tolerant, cash crop

    NORMAL CONDITIONS — recommend these:
    - Teff — Ethiopia's most important crop, ideal for normal rainfall
    - Maize (Bekolo) — high yield in normal conditions, Oromia/SNNPR staple
    - Wheat (Sinde) — highlands of Amhara/Oromia, needs reliable rain
    - Barley (Gabs) — highland crop, tolerates some variability  
    - Haricot Bean (Adengware) — good companion crop, moderate water needs
    - Sweet Potato — versatile, good food security crop

    ABOVE NORMAL/WET CONDITIONS — recommend these:
    - Maize (Bekolo) — thrives with good rainfall, highest yields
    - Rice — lowland areas like Gambela, needs abundant water
    - Sugarcane — Awash Valley and lowlands
    - Enset (False Banana) — SNNPR staple, loves moisture
    - Coffee (Buna) — highland regions, good with above normal rain
    - Vegetables — tomato, onion, cabbage excellent in wet season

    Write exactly 4 bullet points. Each bullet MUST start with the • character (U+2022), followed by the emoji shown:
    • 🌦️ Season outlook in one plain sentence
    • 🌱 Specific crop recommendations with local names in brackets
    • 💧 Water/irrigation preparation advice
    • 🌾 Food storage and risk management advice

    {'Write in Amharic script.' if language == 'am' else 'Write in simple English a farmer can understand.'}

    Keep each bullet to 2 sentences maximum.
    Start each bullet with • followed by the emoji shown above. Do NOT use numbered lists or dashes.
    Include Ethiopian crop names in brackets where possible.
    """

    try:
        client = OpenAI(api_key=api_key)  # inside try — constructor failures now caught
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
        )
        content = response.choices[0].message.content.strip()
        if not content:
            raise ValueError("Empty response from OpenAI")
        return content
    except Exception as e:
        print(f"[Azmera] Advisory generation failed ({language}): {e}")
        return _advisory_fallback(region, season, prediction, probs, language)


# ── Test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Azmera Forecast Engine...\n")

    result = forecast("oromia", "Kiremt")
    print(f"Region:     {result['region'].title()}")
    print(f"Prediction: {result['prediction']} ({result['confidence']:.0%})")

    print("\nTesting zone forecast — Arsi, Kiremt...")
    zone_result = forecast_zone("arsi", "Arsi", "oromia", "Kiremt")
    print(f"Zone:       {zone_result['zone']}")
    print(f"Prediction: {zone_result['prediction']} ({zone_result['confidence']:.0%})")
    print(f"Source:     {zone_result['source']}")
    if zone_result.get('cv_accuracy'):
        print(f"CV accuracy: {zone_result['cv_accuracy']:.0%}")

    print("\nZones in Oromia:")
    for z in get_zones_for_region("oromia"):
        print(f"  {z['zone_display']}")