"""
Azmera - Data Pipeline
========================
Pulls historical climate data for Ethiopian regions from:
- NASA POWER API (rainfall)
- NOAA PSL (ENSO index)
- NOAA PSL (IOD index)

No API keys required for any of these sources.
"""

import requests
import pandas as pd
import os

# ── Output directory ──────────────────────────────────────────────
RAW_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
os.makedirs(RAW_DATA_PATH, exist_ok=True)

# ── Ethiopian Regional Coordinates ───────────────────────────────
# Representative lat/lon for each major region

REGIONS = {
    # Core agricultural regions — highest farming population
    "Oromia":           (7.5081,  38.7651),  # Largest region, ~35% of population
    "Amhara":           (11.5650, 38.0435),  # Northwestern highlands
    "Tigray":           (13.7771, 38.4387),  # Northern region
    "SNNPR":            (6.4523,  36.6913),  # Southern Nations (remaining)
    
    # Newer regions (split from SNNPR post-2020)
    "Sidama":           (6.6642,  38.5457),  # Split from SNNPR in 2020
    "South_West":       (7.2000,  35.8000),  # Split from SNNPR in 2021
    
    # Pastoral/lowland regions — drought vulnerable
    "Afar":             (12.0363, 40.7727),  # Northeastern lowlands
    "Somali":           (6.9295,  43.3290),  # Eastern lowlands
    "Gambela":          (7.6838,  34.3368),  # Western lowlands
    "Benishangul_Gumz": (10.5029, 35.4403),  # Western highlands
    
    # Urban/special regions
    "Addis_Ababa":      (8.9805,  38.7855),  # Capital city
    "Dire_Dawa":        (9.6063,  42.0030),  # Eastern chartered city
    "Harari":           (9.2897,  42.1725),  # Smallest region
}

# ── 1. NASA POWER — Monthly Rainfall ─────────────────────────────
def get_rainfall(lat, lon, start_year=1981, end_year=2024):
    """
    Pull monthly rainfall (mm/day) for a given lat/lon from NASA POWER.
    Designed for agricultural applications, no API key needed.
    """
    print(f"  Fetching rainfall for ({lat}, {lon})...")
    
    url = "https://power.larc.nasa.gov/api/temporal/monthly/point"
    params = {
        "parameters": "PRECTOTCORR",
        "community":  "AG",
        "longitude":  lon,
        "latitude":   lat,
        "start":      start_year,
        "end":        end_year,
        "format":     "JSON"
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    rainfall = data["properties"]["parameter"]["PRECTOTCORR"]

    df = pd.DataFrame(list(rainfall.items()), columns=["date", "rainfall_mm"])

    # Convert date to string and filter out annual summary rows (month 13)
    df = df[df["date"].astype(str).str[-2:] != "13"]
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m")
    df = df.sort_values("date").reset_index(drop=True)

    return df


def pull_all_regions():
    """Pull rainfall data for all Ethiopian regions and save to CSV."""
    print("\n📡 Pulling rainfall data from NASA POWER...")
    
    for region, (lat, lon) in REGIONS.items():
        print(f"\n🌍 Region: {region}")
        df = get_rainfall(lat, lon)
        
        filepath = os.path.join(RAW_DATA_PATH, f"rainfall_{region.lower()}.csv")
        df.to_csv(filepath, index=False)
        print(f"  ✅ Saved → {filepath} ({len(df)} records)")


# ── 2. NOAA — ENSO Index (Niño 3.4) ──────────────────────────────
def get_enso_index():
    """
    Pull monthly ENSO (Niño 3.4) index from NOAA PSL.
    Positive = El Niño (drought risk), Negative = La Niña (wet)
    """
    print("\n📡 Pulling ENSO index from NOAA...")
    
    url = "https://psl.noaa.gov/data/correlation/nina34.anom.data"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    records = []
    for line in response.text.strip().split("\n"):
        values = line.split()
        if len(values) == 13:
            try:
                year = int(values[0])
                for month in range(12):
                    val = float(values[month + 1])
                    if val != -99.99:
                        records.append({
                            "date": pd.Timestamp(year=year, month=month+1, day=1),
                            "enso": val
                        })
            except:
                continue

    df = pd.DataFrame(records)
    filepath = os.path.join(RAW_DATA_PATH, "enso_index.csv")
    df.to_csv(filepath, index=False)
    print(f"  ✅ Saved → {filepath} ({len(df)} records)")
    return df


# ── 3. NOAA — IOD Index (Indian Ocean Dipole) ─────────────────────
def get_iod_index():
    """
    Pull monthly IOD (Dipole Mode Index) from NOAA PSL.
    Strongly linked to Ethiopia's October-December rains.
    """
    print("\n📡 Pulling IOD index from NOAA...")
    
    url = "https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmiwest.had.long.data"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    records = []
    for line in response.text.strip().split("\n"):
        values = line.split()
        if len(values) == 13:
            try:
                year = int(values[0])
                for month in range(12):
                    val = float(values[month + 1])
                    if val != -99.99:
                        records.append({
                            "date": pd.Timestamp(year=year, month=month+1, day=1),
                            "iod": val
                        })
            except:
                continue

    df = pd.DataFrame(records)
    filepath = os.path.join(RAW_DATA_PATH, "iod_index.csv")
    df.to_csv(filepath, index=False)
    print(f"  ✅ Saved → {filepath} ({len(df)} records)")
    return df


# ── 4. NOAA — PDO Index (Pacific Decadal Oscillation) ─────────────
def get_pdo_index():
    """
    Pull monthly PDO index from NOAA PSL.
    Operates on longer timescales than ENSO (decades vs years).
    Modulates how strongly El Niño affects Ethiopian rainfall.
    Positive PDO + El Niño = amplified drought risk
    """
    print("\n📡 Pulling PDO index from NOAA...")
    
    url = "https://psl.noaa.gov/data/correlation/pdo.data"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    records = []
    for line in response.text.strip().split("\n"):
        values = line.split()
        if len(values) == 13:
            try:
                year = int(values[0])
                for month in range(12):
                    val = float(values[month + 1])
                    if abs(val) < 90:  # filter missing values
                        records.append({
                            "date": pd.Timestamp(year=year, month=month+1, day=1),
                            "pdo": val
                        })
            except:
                continue

    df = pd.DataFrame(records)
    filepath = os.path.join(RAW_DATA_PATH, "pdo_index.csv")
    df.to_csv(filepath, index=False)
    print(f"  ✅ Saved → {filepath} ({len(df)} records)")
    return df


# ── 5. NOAA — Atlantic SST Anomaly ────────────────────────────────
def get_atlantic_sst():
    """
    Pull North Atlantic SST anomaly index from NOAA PSL.
    Atlantic warming influences moisture transport to
    western Ethiopian regions (Gambela, Benishangul-Gumz).
    """
    print("\n📡 Pulling Atlantic SST index from NOAA...")
    
    url = "https://psl.noaa.gov/data/correlation/amon.us.data"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    records = []
    for line in response.text.strip().split("\n"):
        values = line.split()
        if len(values) == 13:
            try:
                year = int(values[0])
                for month in range(12):
                    val = float(values[month + 1])
                    if abs(val) < 90:
                        records.append({
                            "date": pd.Timestamp(year=year, month=month+1, day=1),
                            "atlantic_sst": val
                        })
            except:
                continue

    df = pd.DataFrame(records)
    filepath = os.path.join(RAW_DATA_PATH, "atlantic_sst.csv")
    df.to_csv(filepath, index=False)
    print(f"  ✅ Saved → {filepath} ({len(df)} records)")
    return df

# ── 6. CHIRPS — High Resolution Rainfall (via CDS) ────────────────
def get_chirps_rainfall():
    """
    Pull CHIRPS v2.0 monthly rainfall data for Ethiopian regions.
    5km resolution vs NASA POWER's 55km — much better for
    capturing localized drought in highland regions like
    Tigray and Amhara.
    
    Requires: CDS API key in ~/.cdsapirc
    """
    import cdsapi
    import xarray as xr
    import tempfile
    import os

    print("\n📡 Pulling CHIRPS high-resolution rainfall from CDS...")

    # Ethiopia bounding box
    # North, West, South, East
    ETHIOPIA_BBOX = [15.0, 33.0, 3.0, 48.0]

    c = cdsapi.Client(quiet=True)

    # Download CHIRPS monthly data for Ethiopia
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "chirps_ethiopia.nc")

        print("  Requesting CHIRPS data from CDS (this may take 5-10 mins)...")
        c.retrieve(
            "derived-near-surface-meteorological-variables",
            {
                "variable":         "rainfall",
                "product_type":     "monthly_averaged",
                "year":             [str(y) for y in range(1981, 2025)],
                "month":            [f"{m:02d}" for m in range(1, 13)],
                "area":             ETHIOPIA_BBOX,
                "format":           "netcdf"
            },
            filepath
        )

        print("  Processing downloaded data...")
        ds = xr.open_dataset(filepath)
        print(f"  Variables: {list(ds.data_vars)}")
        print(f"  Dimensions: {dict(ds.dims)}")

        # Extract rainfall for each region using coordinates
        records = []
        for region, (lat, lon) in REGIONS.items():
            # Select nearest grid point to region centroid
            region_data = ds.sel(
                lat=lat, lon=lon,
                method="nearest"
            )

            # Get rainfall variable (name varies)
            rain_var = [v for v in ds.data_vars
                       if "rain" in v.lower() or "precip" in v.lower()][0]
            rain_values = region_data[rain_var].values

            # Build dataframe
            times = ds.time.values
            for t, r in zip(times, rain_values):
                records.append({
                    "date":   pd.Timestamp(t).replace(day=1),
                    "region": region,
                    "chirps_rainfall_mm": float(r)
                })

        chirps_df = pd.DataFrame(records)
        chirps_df = chirps_df.sort_values(
            ["region", "date"]
        ).reset_index(drop=True)

        # Save
        filepath_out = os.path.join(RAW_DATA_PATH, "chirps_rainfall.csv")
        chirps_df.to_csv(filepath_out, index=False)
        print(f"  ✅ Saved → {filepath_out} ({len(chirps_df):,} records)")

        return chirps_df
# ── Main ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  Azmera — Data Pipeline")
    print("=" * 50)

    pull_all_regions()
    get_enso_index()
    get_iod_index()
    get_pdo_index()      # ← NEW
    get_atlantic_sst()   # ← NEW
    get_chirps_rainfall()  # ← NEW

    print("\n" + "=" * 50)
    print("  ✅ All data pulled successfully!")
    print(f"  📁 Saved to: {RAW_DATA_PATH}")
    print("=" * 50)