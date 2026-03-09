"""
Azmera — Download & Parse NOAA PSL AMM SST Index
==================================================
Downloads the Atlantic Meridional Mode (AMM) SST index from NOAA PSL and
saves it as data/raw/amm_index.csv for use in Phase E Belg experiments.

Source:
  https://psl.noaa.gov/data/correlation/amm.data
  Original data from: https://www.aos.wisc.edu/dvimont/MModes/Data.html
  (Vimont & Kossin AMM SST index)

File format (fixed-width, space-delimited):
  Line 1:   <start_year>  <end_year>        ← header, skip
  Lines 2+: <year>  <Jan>  <Feb>  …  <Dec> ← 12 monthly values
  Footer:   lines starting with non-numeric content (e.g. source info)
  Missing:  -99.000 or any value < -90 → treated as NaN

Units: weighted SST anomaly (°C, scaled by EOF pattern) — values typically
  in the range −8 to +8. Larger magnitude than AMO (±0.7 °C) because this
  is a pattern-amplitude index, not a simple area average.

Output: data/raw/amm_index.csv
  Columns: date (YYYY-MM-01), amm_sst (float, NaN for missing)

Operational realism for Belg (March–May, issued late February):
  amm_sst_jan  = January AMM of forecast year    (published ~Feb 15 ✓ SAFE)
  amm_sst_dec  = December AMM of prior year      (published ~Jan 15 ✓ SAFE)
  amm_sst_feb  = February AMM                    (published ~Mar 15 ✗ NOT SAFE)
  → Phase E uses amm_lag2 (Jan) and amm_lag3 (Dec) only.

Run:
  python scripts/download_amm_index.py
"""

import subprocess
import pandas as pd
import numpy as np
import os
import sys

AMM_URL  = "https://psl.noaa.gov/data/correlation/amm.data"
OUT_PATH = "data/raw/amm_index.csv"
SENTINEL = -90.0          # values ≤ this are missing
MONTHS   = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fetch_raw(url: str, timeout: int = 30) -> str:
    """Download text content from URL using curl (avoids macOS SSL cert issues)."""
    print(f"Fetching {url} …")
    result = subprocess.run(
        ["curl", "-s", "--max-time", str(timeout), url],
        capture_output=True, text=True, check=True,
    )
    raw = result.stdout
    if not raw.strip():
        raise RuntimeError(f"curl returned empty response from {url}")
    print(f"  Downloaded {len(raw):,} bytes.")
    return raw


def parse_amm(raw_text: str) -> pd.DataFrame:
    """
    Parse the NOAA PSL AMM fixed-width text into a tidy monthly DataFrame.

    Returns:
        DataFrame with columns: date (datetime), amm_sst (float)
        One row per month; missing values are NaN.
    """
    lines = raw_text.splitlines()

    records = []
    header_seen = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Split on whitespace
        parts = stripped.split()

        # First non-empty line is the header "start_year  end_year"
        if not header_seen:
            if len(parts) == 2 and parts[0].lstrip("-").isdigit():
                header_seen = True
                continue
            continue

        # Data line: first token must be a 4-digit year
        if not (len(parts) >= 2 and len(parts[0]) == 4 and parts[0].isdigit()):
            continue   # footer or metadata line — skip

        year = int(parts[0])
        if year < 1900 or year > 2100:
            continue

        monthly_vals = parts[1:]   # up to 12 values
        for m_idx, raw_val in enumerate(monthly_vals[:12]):
            try:
                val = float(raw_val)
            except ValueError:
                val = np.nan
            if val <= SENTINEL:
                val = np.nan
            month = m_idx + 1
            records.append({
                "date":    pd.Timestamp(f"{year}-{month:02d}-01"),
                "amm_sst": val,
            })

    df = pd.DataFrame(records)
    df = df.sort_values("date").reset_index(drop=True)
    return df


def verify(df: pd.DataFrame) -> None:
    """Print a brief QC summary."""
    total   = len(df)
    missing = df["amm_sst"].isna().sum()
    valid   = total - missing

    print(f"\nQC Summary:")
    print(f"  Total monthly rows : {total}")
    print(f"  Valid (non-NaN)    : {valid}")
    print(f"  Missing (NaN)      : {missing}")
    print(f"  Date range         : {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"  AMM SST range      : {df['amm_sst'].min():.3f} → {df['amm_sst'].max():.3f}")
    print(f"  AMM SST mean±std   : {df['amm_sst'].mean():.3f} ± {df['amm_sst'].std():.3f}")

    # Spot-check: January 1958 should be ~1.41
    jan1958 = df[df["date"] == pd.Timestamp("1958-01-01")]["amm_sst"].values
    if len(jan1958):
        print(f"  Spot-check Jan 1958: {jan1958[0]:.3f}  (expect ≈ 1.41)")

    # Check coverage for Phase E rolling-origin years (1981–2021)
    ro_years = df[df["date"].dt.year.between(1981, 2021)]
    full_months = ro_years.groupby(ro_years["date"].dt.year).size()
    incomplete  = (full_months < 12).sum()
    if incomplete:
        print(f"  ⚠️  {incomplete} rolling-origin years with < 12 months of data")
    else:
        print(f"  ✓  All rolling-origin years (1981–2021) have complete 12-month coverage")


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    raw  = fetch_raw(AMM_URL)
    df   = parse_amm(raw)
    verify(df)

    df.to_csv(OUT_PATH, index=False)
    print(f"\nSaved: {OUT_PATH}  ({len(df)} rows)")
    print("\nOperational features for Phase E Belg rolling-origin:")
    print("  amm_sst_jan = AMM for January of forecast year   (available late Feb ✓)")
    print("  amm_sst_dec = AMM for December of prior year     (available late Feb ✓)")
    print("  amm_sst_feb = February AMM                       (NOT available late Feb ✗)")


if __name__ == "__main__":
    main()
