"""
Azmera — Zone-level CHIRPS Data Pipeline
Pulls 1981–2024 seasonal rainfall for all 79 Ethiopian zones from GEE.
Run once to build the training dataset for zone-level forecasting.
"""

import ee
import pandas as pd
import numpy as np
from datetime import datetime
import json
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

# ── Init GEE ─────────────────────────────────────────────────────
def init_gee():
    key_path = os.path.expanduser("~/secrets/azmera-gee-key.json")
    with open(key_path) as f:
        key_dict = json.load(f)
    credentials = ee.ServiceAccountCredentials(key_dict["client_email"], key_path)
    ee.Initialize(credentials)
    print("GEE connected.")

# ── Season definitions ────────────────────────────────────────────
SEASONS = {
    "Kiremt": {"start_month": 6, "end_month": 9},   # Jun–Sep
    "Belg":   {"start_month": 3, "end_month": 5},   # Mar–May
}

# ── Pull seasonal CHIRPS rainfall for one zone/year/season ────────
def get_chirps_seasonal(lat, lon, year, season_key, buffer_km=25000):
    """Get total seasonal rainfall (mm) for a point, given year and season."""
    s = SEASONS[season_key]
    start = f"{year}-{s['start_month']:02d}-01"
    # End of last month
    if s['end_month'] == 12:
        end = f"{year+1}-01-01"
    else:
        end = f"{year}-{s['end_month']+1:02d}-01"

    point = ee.Geometry.Point([lon, lat]).buffer(buffer_km)

    total = (
        ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
        .filterDate(start, end)
        .sum()
        .reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=point,
            scale=5000,
            maxPixels=1e9
        )
        .getInfo()
    )
    return total.get("precipitation", None)


# ── Compute SPI from a rainfall series ───────────────────────────
def compute_spi(series):
    """
    Compute SPI (Standardized Precipitation Index) from a rainfall series.
    SPI = (x - mean) / std
    """
    arr = np.array(series, dtype=float)
    mean = np.nanmean(arr)
    std  = np.nanstd(arr)
    if std == 0:
        return [0.0] * len(arr)
    return ((arr - mean) / std).tolist()


# ── Classify SPI into target ──────────────────────────────────────
def spi_to_target(spi):
    if spi < -0.5:
        return 0  # Below Normal
    elif spi > 0.5:
        return 2  # Above Normal
    else:
        return 1  # Near Normal


# ── Main pipeline ─────────────────────────────────────────────────
def build_zone_dataset():
    init_gee()

    # Load zone centroids
    centroids = pd.read_csv("data/zone_centroids.csv")
    print(f"Loaded {len(centroids)} zones.")

    years = list(range(1981, 2025))
    records = []
    total = len(centroids) * len(SEASONS) * len(years)
    done = 0

    for _, zone in centroids.iterrows():
        zone_key    = zone["zone_key"]
        region_key  = zone["region_key"]
        zone_display = zone["zone_display"]
        lat = zone["lat"]
        lon = zone["lon"]

        for season_key in SEASONS:
            print(f"\n{zone_display} — {season_key} ({len(years)} years)...")
            rainfall_series = []

            for year in years:
                try:
                    mm = get_chirps_seasonal(lat, lon, year, season_key)
                    rainfall_series.append(mm)
                    done += 1
                    if done % 50 == 0:
                        pct = done / total * 100
                        print(f"  Progress: {done}/{total} ({pct:.1f}%)")
                except Exception as e:
                    print(f"  Error {zone_display} {season_key} {year}: {e}")
                    rainfall_series.append(None)
                    done += 1

                # Small delay to avoid GEE rate limits
                time.sleep(0.1)

            # Compute SPI for this zone/season
            valid = [r for r in rainfall_series if r is not None]
            spi_values = compute_spi(rainfall_series) if len(valid) > 10 else [None] * len(years)

            for i, year in enumerate(years):
                mm  = rainfall_series[i]
                spi = spi_values[i] if spi_values[i] is not None else None
                target = spi_to_target(spi) if spi is not None else None

                records.append({
                    "zone_key":     zone_key,
                    "region_key":   region_key,
                    "zone_display": zone_display,
                    "year":         year,
                    "season":       season_key,
                    "rainfall_mm":  round(mm, 2) if mm else None,
                    "spi":          round(spi, 4) if spi else None,
                    "target":       target,
                    "lat":          lat,
                    "lon":          lon,
                })

    df = pd.DataFrame(records)

    # Save raw rainfall
    out_path = "data/processed/zone_rainfall.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\nSaved {len(df)} records to {out_path}")
    print(f"Zones: {df['zone_key'].nunique()}")
    print(f"Years: {df['year'].min()}–{df['year'].max()}")
    print(f"Null rainfall: {df['rainfall_mm'].isna().sum()}")

    return df


if __name__ == "__main__":
    print("Starting zone CHIRPS pipeline...")
    print("This will take 20-40 minutes for 79 zones × 2 seasons × 44 years.")
    print("GEE Community tier usage: ~5-8 EECU-hours\n")
    df = build_zone_dataset()
    print("\nDone! Next step: run build_zone_models.py")
