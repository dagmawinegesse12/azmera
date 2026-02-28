import requests, gzip, os, sys
import numpy as np
import pandas as pd
from rasterio.io import MemoryFile

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/chirps_baseline.csv")

REGIONS = {
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

SEASONS = {"Kiremt": [6, 7, 8, 9], "Belg": [3, 4, 5]}

def fetch_chirps(year, month):
    url = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs/chirps-v2.0.{}.{:02d}.tif.gz".format(year, month)
    try:
        r = requests.get(url, timeout=60)
        if r.status_code != 200:
            return None
        return gzip.decompress(r.content)
    except Exception as e:
        print("fetch error {}-{}: {}".format(year, month, e), flush=True)
        return None

def extract_value(data, lat, lon):
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
    except Exception as e:
        print("extract error ({},{}): {}".format(lat, lon, e), flush=True)
        return 0.0

records = []

for season, months in SEASONS.items():
    print("=== {} (months {}) ===".format(season, months), flush=True)
    for year in range(1991, 2021):
        print("  {}...".format(year), end=" ", flush=True)
        month_data = {}
        for month in months:
            data = fetch_chirps(year, month)
            if data:
                month_data[month] = data
        if len(month_data) < len(months):
            print("missing, skipping", flush=True)
            continue
        for region, (lat, lon) in REGIONS.items():
            total = sum(extract_value(month_data[m], lat, lon) for m in months)
            records.append({"region": region, "season": season, "year": year, "total_mm": round(total, 1)})
        print("done", flush=True)

df = pd.DataFrame(records)
baseline = (
    df.groupby(["region", "season"])["total_mm"]
    .agg(baseline_mean="mean", baseline_std="std", baseline_median="median")
    .reset_index()
    .round(1)
)
baseline.to_csv(OUTPUT, index=False)
print("Saved to " + OUTPUT)
print(baseline.to_string())
