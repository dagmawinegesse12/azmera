"""
Azmera - CHIRPS Rainfall Anomaly
Fetches current season rainfall and compares to 1991-2020 baseline.
"""

import requests, gzip, os
import numpy as np
import pandas as pd
from datetime import datetime
from rasterio.io import MemoryFile
import streamlit as st

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
BASELINE_CSV = os.path.join(BASE_DIR, "../data/chirps_baseline.csv")

REGION_COORDS = {
    "tigray":           (14.0, 38.5),
    "afar":             (12.0, 41.5),
    "amhara":           (11.5, 38.0),
    "oromia":           (7.5,  39.5),
    "somali":           (6.5,  44.0),
    "benishangul_gumz": (10.5, 35.5),
    "snnpr":            (6.5,  37.5),
    "gambela":          (8.0,  34.5),
    "harari":           (9.3,  42.1),
    "dire_dawa":        (9.6,  41.9),
    "addis_ababa":      (9.0,  38.7),
}

SEASON_MONTHS = {
    "Kiremt": [6, 7, 8, 9],
    "Belg":   [3, 4, 5],
    "OND":    [10, 11, 12],
    "Bega":   [1, 2],
}


def _fetch_chirps(year, month):
    url = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs/chirps-v2.0.{}.{:02d}.tif.gz".format(year, month)
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            return None
        return gzip.decompress(r.content)
    except Exception:
        return None


def _extract_value(data, lat, lon):
    try:
        with MemoryFile(data) as memfile:
            with memfile.open() as ds:
                band = ds.read(1).astype(float)
                band[band < -9000] = np.nan
                row, col = ds.index(lon, lat)
                val = float(band[row, col])
                if np.isnan(val):
                    window = band[max(0,row-1):row+2, max(0,col-1):col+2]
                    val = float(np.nanmean(window))
                return val
    except Exception:
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def get_latest_month_rainfall(region_key):
    """Get the most recent available CHIRPS month for a region."""
    lat, lon = REGION_COORDS.get(region_key, (9.0, 38.7))
    now = datetime.now()
    for delta in range(0, 3):
        month = now.month - 1 - delta
        year  = now.year
        while month < 1:
            month += 12
            year  -= 1
        data = _fetch_chirps(year, month)
        if data:
            val = _extract_value(data, lat, lon)
            if val is not None:
                return {
                    "month":    month,
                    "year":     year,
                    "rainfall": round(val, 1),
                    "label":    datetime(year, month, 1).strftime("%B %Y"),
                }
    return None


@st.cache_data(ttl=86400, show_spinner=False)
def get_season_anomaly(region_key, season):
    """
    Get completed or in-progress season rainfall vs 1991-2020 baseline.
    Returns dict with total, baseline, anomaly_pct, months_available.
    """
    lat, lon    = REGION_COORDS.get(region_key, (9.0, 38.7))
    months      = SEASON_MONTHS.get(season, [6, 7, 8, 9])
    baseline_df = pd.read_csv(BASELINE_CSV)
    row         = baseline_df[
        (baseline_df["region"] == region_key) &
        (baseline_df["season"] == season)
    ]
    if row.empty:
        return None
    baseline_mean = float(row["baseline_mean"].values[0])
    baseline_std  = float(row["baseline_std"].values[0])

    now  = datetime.now()
    year = now.year
    if now.month < months[0]:
        year -= 1

    total     = 0.0
    available = []
    for month in months:
        if year == now.year and month > now.month - 1:
            break
        data = _fetch_chirps(year, month)
        if data:
            val = _extract_value(data, lat, lon)
            if val is not None:
                total += val
                available.append(month)

    if not available:
        return None

    anomaly_pct = (total - baseline_mean) / baseline_mean * 100
    z_score     = (total - baseline_mean) / baseline_std if baseline_std > 0 else 0

    if anomaly_pct > 15:    status = "Above Normal"
    elif anomaly_pct < -15: status = "Below Normal"
    else:                   status = "Near Normal"

    completed = len(available) == len(months)

    return {
        "season":           season,
        "year":             year,
        "total_mm":         round(total, 1),
        "baseline_mean":    round(baseline_mean, 1),
        "baseline_std":     round(baseline_std, 1),
        "anomaly_pct":      round(anomaly_pct, 1),
        "z_score":          round(z_score, 2),
        "status":           status,
        "months_available": available,
        "completed":        completed,
        "label":            "Full season" if completed else "Season-to-date",
    }


# ── Zone centroid coords (loaded once) ───────────────────────────
_ZONE_CENTROIDS = None

def _get_zone_centroids():
    global _ZONE_CENTROIDS
    if _ZONE_CENTROIDS is not None:
        return _ZONE_CENTROIDS
    path = os.path.join(BASE_DIR, "../data/zone_centroids.csv")
    df = pd.read_csv(path)
    _ZONE_CENTROIDS = df.drop_duplicates("zone_key").set_index("zone_key")[["lat", "lon"]].to_dict("index")
    return _ZONE_CENTROIDS


# ── Zone baseline (loaded once) ───────────────────────────────────
_ZONE_BASELINE = None

def _get_zone_baseline():
    global _ZONE_BASELINE
    if _ZONE_BASELINE is not None:
        return _ZONE_BASELINE
    path = os.path.join(BASE_DIR, "../data/zone_chirps_baseline.csv")
    df = pd.read_csv(path)
    _ZONE_BASELINE = df.set_index(["zone_key", "season"]).to_dict("index")
    return _ZONE_BASELINE


@st.cache_data(ttl=86400, show_spinner=False)
def get_zone_spi_lag1(zone_key, season):
    """
    Compute real spi_lag1 for a zone at inference time.
    For a 2026 Kiremt forecast, fetches 2025 Kiremt CHIRPS for the zone
    centroid and computes SPI against the 1991-2020 zone baseline.
    Cached daily. Falls back to 0.0 (neutral) if data unavailable.
    """
    centroids = _get_zone_centroids()
    baseline  = _get_zone_baseline()

    if zone_key not in centroids:
        return 0.0

    baseline_key = (zone_key, season)
    if baseline_key not in baseline:
        return 0.0

    lat           = centroids[zone_key]["lat"]
    lon           = centroids[zone_key]["lon"]
    baseline_mean = baseline[baseline_key]["baseline_mean"]
    baseline_std  = baseline[baseline_key]["baseline_std"]

    if baseline_std <= 0:
        return 0.0

    season_months = SEASON_MONTHS.get(season, [6, 7, 8, 9])
    prev_year     = datetime.now().year - 1

    total     = 0.0
    available = []

    for month in season_months:
        data = _fetch_chirps(prev_year, month)
        if data:
            val = _extract_value(data, lat, lon)
            if val is not None:
                total += val
                available.append(month)

    if len(available) < len(season_months) // 2:
        return 0.0

    if len(available) < len(season_months):
        total = total * len(season_months) / len(available)

    spi = (total - baseline_mean) / baseline_std
    return float(max(-3.0, min(3.0, spi)))
