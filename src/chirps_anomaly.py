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
