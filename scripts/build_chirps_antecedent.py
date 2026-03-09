"""
Azmera — CHIRPS Belg Antecedent Historical Download
====================================================
Downloads CHIRPS monthly rainfall for Belg months (Mar–Apr–May) for each
region and year 1981–2023. Computes the standardised anomaly z-score
(belg_antecedent_anom_z) used as the antecedent feature for Kiremt models.

Feature name rationale:
  belg_antecedent_anom_z — Belg-season antecedent precipitation anomaly,
  expressed as a z-score against the 1991–2020 CHIRPS climatology.
  This is NOT gamma-SPI (no gamma fitting); it is a simple standardised
  anomaly: z = (total_mm - baseline_mean) / baseline_std, clamped ±3.

Outputs:
  data/chirps_belg_historical.csv
    Columns: region, year, belg_total_mm, belg_antecedent_anom_z

Also updates chirps_baseline.csv to add sidama and south_west Belg rows
if they are not already present.

Run from project root:
    python scripts/build_chirps_antecedent.py

Download cost: 3 months × 43 years = 129 CHIRPS files (~4–8 MB each, gzip).
Each raster is downloaded once; all 13 regions extracted from it, then discarded.
Estimated time: 15–40 min depending on network.
"""

import requests
import gzip
import os
import sys
import numpy as np
import pandas as pd
from rasterio.io import MemoryFile

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_CSV  = os.path.join(BASE_DIR, "data", "chirps_belg_historical.csv")
BASELINE_CSV = os.path.join(BASE_DIR, "data", "chirps_baseline.csv")

# ── Region representative coordinates ─────────────────────────────────────────
# Match REGION_COORDS in src/chirps_anomaly.py exactly
REGIONS = {
    "tigray":           (14.0, 38.5),
    "afar":             (12.0, 41.5),
    "amhara":           (11.5, 38.0),
    "oromia":           (7.5,  39.5),
    "somali":           (6.5,  44.0),
    "benishangul_gumz": (10.5, 35.5),
    "snnpr":            (6.5,  37.5),
    "sidama":           (6.8,  38.5),   # previously missing from chirps_baseline.csv
    "south_west":       (7.0,  35.6),   # previously missing from chirps_baseline.csv
    "gambela":          (8.0,  34.5),
    "harari":           (9.3,  42.1),
    "dire_dawa":        (9.6,  41.9),
    "addis_ababa":      (9.0,  38.7),
}

# Belg months — antecedent for Kiremt forecasts.
# Ends May 31; Kiremt starts June 1 → zero leakage into the target season.
BELG_MONTHS = [3, 4, 5]

# Year range: covers full training period (1981–2022) plus one extra year.
FIRST_YEAR = 1981
LAST_YEAR  = 2023

# Baseline reference period (WMO standard 1991–2020)
BASELINE_START = 1991
BASELINE_END   = 2020


# ── CHIRPS download helpers ────────────────────────────────────────────────────

def _fetch_chirps(year, month):
    url = (
        "https://data.chc.ucsb.edu/products/CHIRPS-2.0/"
        "africa_monthly/tifs/chirps-v2.0.{}.{:02d}.tif.gz"
    ).format(year, month)
    try:
        r = requests.get(url, timeout=60)
        if r.status_code != 200:
            print(f"    HTTP {r.status_code} for {year}-{month:02d}", flush=True)
            return None
        return gzip.decompress(r.content)
    except Exception as e:
        print(f"    fetch error {year}-{month:02d}: {e}", flush=True)
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
                    window = band[max(0, row-1):row+2, max(0, col-1):col+2]
                    val = float(np.nanmean(window))
                return val
    except Exception as e:
        print(f"    extract error ({lat},{lon}): {e}", flush=True)
        return np.nan


# ── Main download loop ─────────────────────────────────────────────────────────

def build_antecedent_dataset():
    print("=" * 68)
    print("Azmera — CHIRPS Belg Antecedent Historical Download")
    print("=" * 68)
    print(f"Years:   {FIRST_YEAR}–{LAST_YEAR}")
    print(f"Months:  Mar–Apr–May (Belg antecedent for Kiremt)")
    print(f"Regions: {len(REGIONS)}")
    n_downloads = (LAST_YEAR - FIRST_YEAR + 1) * len(BELG_MONTHS)
    print(f"Downloads: {n_downloads} CHIRPS files (one raster per year-month)")
    print("=" * 68)

    # Accumulate per (region, year, month)
    rows = []

    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        print(f"\n{year}:", end="  ", flush=True)
        # Download each month's raster; extract all regions from it; then discard
        month_totals = {region: [] for region in REGIONS}

        for month in BELG_MONTHS:
            print(f"month={month}", end=" ", flush=True)
            raster = _fetch_chirps(year, month)
            if raster is None:
                print("(skip)", end=" ", flush=True)
                for region in REGIONS:
                    month_totals[region].append(np.nan)
                continue
            for region, (lat, lon) in REGIONS.items():
                val = _extract_value(raster, lat, lon)
                month_totals[region].append(val)
            # Raster goes out of scope here → freed
            del raster

        # Sum over available months; require all 3 months for a valid total
        for region in REGIONS:
            vals = month_totals[region]
            if any(np.isnan(v) for v in vals):
                total = np.nan
            else:
                total = sum(vals)
            rows.append({"region": region, "year": year, "belg_total_mm": total})

        print("✓", flush=True)

    raw_df = pd.DataFrame(rows)
    print(f"\nDownloaded: {raw_df['belg_total_mm'].notna().sum()} valid region-year totals "
          f"out of {len(raw_df)}")

    # ── Compute 1991–2020 baseline per region ──────────────────────────────────
    baseline_df = (
        raw_df[raw_df["year"].between(BASELINE_START, BASELINE_END)]
        .groupby("region")["belg_total_mm"]
        .agg(mean="mean", std="std")
        .reset_index()
    )
    print("\n1991–2020 Belg baseline (mm, Mar–Apr–May total):")
    for _, row in baseline_df.iterrows():
        print(f"  {row['region']:<22} mean={row['mean']:6.1f}  std={row['std']:5.1f}")

    # ── Compute z-score: (total - mean) / std, clamped ±3.0 ──────────────────
    raw_df = raw_df.merge(baseline_df, on="region", how="left")
    raw_df["belg_antecedent_anom_z"] = np.where(
        raw_df["belg_total_mm"].notna() & (raw_df["std"] > 0),
        np.clip(
            (raw_df["belg_total_mm"] - raw_df["mean"]) / raw_df["std"],
            -3.0, 3.0
        ),
        np.nan
    )

    # ── Save ──────────────────────────────────────────────────────────────────
    out = raw_df[["region", "year", "belg_total_mm", "belg_antecedent_anom_z"]].round(4)
    out = out.sort_values(["region", "year"]).reset_index(drop=True)
    out.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved: {OUTPUT_CSV}  ({len(out)} rows)")

    valid = out["belg_antecedent_anom_z"].notna().sum()
    print(f"Valid z-scores: {valid}/{len(out)}  "
          f"({valid/len(out)*100:.0f}%)")
    print(f"z-score range: [{out['belg_antecedent_anom_z'].min():.2f}, "
          f"{out['belg_antecedent_anom_z'].max():.2f}]")

    # ── Extend chirps_baseline.csv with sidama and south_west if needed ───────
    _extend_baseline(baseline_df)

    return out


def _extend_baseline(new_baseline_df):
    """Add sidama and south_west Belg rows to chirps_baseline.csv if missing."""
    existing = pd.read_csv(BASELINE_CSV)
    missing_regions = []
    for region in ["sidama", "south_west"]:
        already = (
            (existing["region"] == region) & (existing["season"] == "Belg")
        ).any()
        if not already:
            missing_regions.append(region)

    if not missing_regions:
        print("\nchirps_baseline.csv already has sidama and south_west — no update needed.")
        return

    new_rows = []
    for region in missing_regions:
        row = new_baseline_df[new_baseline_df["region"] == region]
        if row.empty:
            print(f"  WARNING: no baseline computed for {region} — skipping.")
            continue
        new_rows.append({
            "region":          region,
            "season":          "Belg",
            "baseline_mean":   round(float(row["mean"].values[0]), 1),
            "baseline_std":    round(float(row["std"].values[0]),  1),
            "baseline_median": round(float(row["mean"].values[0]), 1),  # approx
        })
        print(f"  Adding {region} Belg to chirps_baseline.csv: "
              f"mean={new_rows[-1]['baseline_mean']:.1f}  "
              f"std={new_rows[-1]['baseline_std']:.1f}")

    if new_rows:
        updated = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)
        updated = updated.sort_values(["region", "season"]).reset_index(drop=True)
        updated.to_csv(BASELINE_CSV, index=False)
        print(f"  chirps_baseline.csv updated: {len(updated)} rows total")


if __name__ == "__main__":
    df = build_antecedent_dataset()
    print("\nSample (oromia, sorted by year):")
    print(df[df["region"] == "oromia"].to_string(index=False))
    print("\nDone.")
