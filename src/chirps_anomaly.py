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
    # Sidama: representative coord near Hawassa (~regional centre)
    "sidama":           (6.8,  38.5),
    # South West: representative coord near Mizan Teferi
    "south_west":       (7.0,  35.6),
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


# ── Raster cache: one download per (year, month) ─────────────────
# Cap at 12 entries (≈3 months × 4 seasons) to prevent unbounded memory growth.
# Each decompressed CHIRPS Africa monthly TIF is ~4–8 MB.
_RASTER_CACHE: dict = {}
_RASTER_CACHE_MAX = 12


def _fetch_chirps_cached(year, month):
    """Download CHIRPS raster once per (year, month) and reuse in memory.
    Evicts oldest entry when cache exceeds _RASTER_CACHE_MAX."""
    key = (year, month)
    if key not in _RASTER_CACHE:
        if len(_RASTER_CACHE) >= _RASTER_CACHE_MAX:
            # Remove oldest key (insertion-order guaranteed in Python 3.7+)
            oldest = next(iter(_RASTER_CACHE))
            del _RASTER_CACHE[oldest]
        _RASTER_CACHE[key] = _fetch_chirps(year, month)
    return _RASTER_CACHE[key]


@st.cache_data(ttl=86400, show_spinner=False)
def get_season_spi_lag1_all_zones(season):
    """
    Batch-compute spi_lag1 for ALL zones in one pass.
    Downloads each monthly CHIRPS raster ONCE, extracts all zone coords.
    Returns dict: {zone_key: spi_value}
    Cached daily — called once per season, reused for all zones.
    """
    centroids     = _get_zone_centroids()
    baseline      = _get_zone_baseline()
    season_months = SEASON_MONTHS.get(season, [6, 7, 8, 9])
    prev_year     = datetime.now().year - 1

    # Accumulate totals per zone
    totals    = {zk: 0.0 for zk in centroids}
    available = {zk: 0   for zk in centroids}

    for month in season_months:
        data = _fetch_chirps_cached(prev_year, month)
        if data is None:
            continue
        # Extract all zone coords from this single raster
        for zone_key, coords in centroids.items():
            val = _extract_value(data, coords["lat"], coords["lon"])
            if val is not None:
                totals[zone_key]    += val
                available[zone_key] += 1

    # Compute SPI per zone
    results = {}
    for zone_key in centroids:
        n = available[zone_key]
        if n < len(season_months) // 2:
            results[zone_key] = 0.0
            continue
        baseline_key = (zone_key, season)
        if baseline_key not in baseline:
            results[zone_key] = 0.0
            continue
        bm  = baseline[baseline_key]["baseline_mean"]
        bsd = baseline[baseline_key]["baseline_std"]
        if bsd <= 0:
            results[zone_key] = 0.0
            continue
        total = totals[zone_key]
        if n < len(season_months):
            total = total * len(season_months) / n  # scale up partial season
        spi = (total - bm) / bsd
        results[zone_key] = float(max(-3.0, min(3.0, spi)))

    return results


@st.cache_data(ttl=86400, show_spinner=False)
def get_zone_spi_lag1(zone_key, season):
    """
    Get spi_lag1 for a single zone. Uses batch cache — no extra downloads.
    Falls back to 0.0 (neutral) if data unavailable.
    """
    all_spis = get_season_spi_lag1_all_zones(season)
    return all_spis.get(zone_key, 0.0)


@st.cache_data(ttl=86400, show_spinner=False)
def get_region_belg_antecedent_anom_z(region_key, target_season):
    """
    Compute belg_antecedent_anom_z for a region at inference time.

    For Kiremt forecasts:
      Returns the z-score of Belg (Mar–May) rainfall for the current forecast
      year, standardised against the 1991–2020 CHIRPS Belg climatology stored
      in chirps_baseline.csv.

      z = (belg_total_mm − baseline_mean) / baseline_std, clamped ±3.0

      Feature name: belg_antecedent_anom_z
      This is NOT gamma-SPI. It is a simple standardised anomaly (same method
      used in build_chirps_antecedent.py and validate_rolling_origin.py).

    For Belg forecasts:
      Returns 0.0 — no clean DJF antecedent baseline exists.

    Falls back to 0.0 on any CHIRPS download failure or missing baseline.
    This is safe: the model was trained with real values but L2 regularisation
    (C=0.5) limits the impact of a neutral 0.0 fallback.

    Implementation reuses get_season_anomaly() which already handles:
      • year inference from current date (current year for Jun–Oct calls)
      • partial-season scaling (if May CHIRPS is delayed)
      • CHIRPS download with fallback
    """
    if target_season != "Kiremt":
        return 0.0   # Belg antecedent deferred — no clean DJF baseline

    result = get_season_anomaly(region_key, "Belg")
    if result is None:
        return 0.0
    z = result.get("z_score", 0.0)
    if z is None or (isinstance(z, float) and (z != z)):   # NaN check
        return 0.0
    return float(max(-3.0, min(3.0, z)))
