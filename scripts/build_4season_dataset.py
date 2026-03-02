"""
Azmera — 4-Season Dataset Builder
Builds seasonal_4seasons.parquet from raw climate indices and CHIRPS rainfall.

Seasons:
  Kiremt: Jun-Sep  (lag: Mar-May)   — Main rains, all regions
  Belg:   Mar-May  (lag: Dec-Feb)   — Short rains, central/south
  OND:    Oct-Dec  (lag: Jul-Sep)   — Short rains, Somali/SNNPR/Sidama
  Bega:   Jan-Feb  (lag: Oct-Nov)   — Dry season rains, Afar/Somali pastoralists

Run from project root:
    python scripts/build_4season_dataset.py

Outputs:
    data/processed/seasonal_4seasons.parquet
"""

import pandas as pd
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_indices():
    enso = pd.read_csv(f'{BASE_DIR}/data/raw/enso_index.csv',    parse_dates=['date']).sort_values('date')
    iod  = pd.read_csv(f'{BASE_DIR}/data/raw/iod_index.csv',     parse_dates=['date']).sort_values('date')
    pdo  = pd.read_csv(f'{BASE_DIR}/data/raw/pdo_index.csv',     parse_dates=['date']).sort_values('date')
    atl  = pd.read_csv(f'{BASE_DIR}/data/raw/atlantic_sst.csv',  parse_dates=['date']).sort_values('date')

    iod  = iod[iod['iod'].abs()        < 90]
    pdo  = pdo[pdo['pdo'].abs()        < 9]
    enso = enso[enso['enso'].notna()]
    atl  = atl[atl['atlantic_sst'].notna()]

    def to_monthly(df, col):
        df = df.copy()
        df['ym'] = df['date'].dt.to_period('M')
        return df.set_index('ym')[col]

    return (
        to_monthly(enso, 'enso'),
        to_monthly(iod,  'iod'),
        to_monthly(pdo,  'pdo'),
        to_monthly(atl,  'atlantic_sst'),
    )

def get_val(series, year, month):
    try:
        return float(series[pd.Period(f'{year}-{month:02d}', 'M')])
    except:
        return np.nan

SEASONS = {
    'Kiremt': ([6,7,8,9],  [3,4,5]),
    'Belg':   ([3,4,5],    [12,1,2]),
    'OND':    ([10,11,12], [7,8,9]),
    'Bega':   ([1,2],      [10,11]),
}

REGIONS = [
    'addis_ababa','afar','amhara','benishangul_gumz','dire_dawa',
    'gambela','harari','oromia','sidama','snnpr','somali','south_west','tigray'
]

def build_dataset():
    enso_m, iod_m, pdo_m, atl_m = load_indices()

    rainfall = {}
    for r in REGIONS:
        df = pd.read_csv(f'{BASE_DIR}/data/raw/rainfall_{r}.csv', parse_dates=['date'])
        df['ym'] = df['date'].dt.to_period('M')
        rainfall[r] = df.set_index('ym')['rainfall_mm']

    rows = []

    for year in range(1981, 2024):
        for season_name, (rain_months, lag_months) in SEASONS.items():

            # Handle Belg Dec lag crossing year boundary
            adjusted_lags = []
            for m in lag_months:
                if m > 9 and season_name == 'Belg':
                    adjusted_lags.append((year-1, m))
                else:
                    adjusted_lags.append((year, m))

            l1 = adjusted_lags[-1] if len(adjusted_lags) >= 1 else (year, lag_months[-1])
            l2 = adjusted_lags[-2] if len(adjusted_lags) >= 2 else l1
            l3 = adjusted_lags[0]  if len(adjusted_lags) >= 3 else l2

            enso1 = get_val(enso_m, *l1); enso2 = get_val(enso_m, *l2); enso3 = get_val(enso_m, *l3)
            iod1  = get_val(iod_m,  *l1); iod2  = get_val(iod_m,  *l2); iod3  = get_val(iod_m,  *l3)
            pdo1  = get_val(pdo_m,  *l1); pdo2  = get_val(pdo_m,  *l2); pdo3  = get_val(pdo_m,  *l3)
            atl1  = get_val(atl_m,  *l1); atl2  = get_val(atl_m,  *l2); atl3  = get_val(atl_m,  *l3)

            enso_mean = np.nanmean([enso1, enso2, enso3])
            iod_mean  = np.nanmean([iod1,  iod2,  iod3])
            pdo_mean  = np.nanmean([pdo1,  pdo2,  pdo3])
            atl_mean  = np.nanmean([atl1,  atl2,  atl3])

            for region in REGIONS:
                total_rain = [get_val(rainfall[region], year, m) for m in rain_months]
                total_rain = [v for v in total_rain if not np.isnan(v)]
                if len(total_rain) < len(rain_months) * 0.5:
                    continue
                total = sum(total_rain)

                # Baseline 1981-2020
                baseline = []
                for by in range(1981, 2021):
                    bt = [get_val(rainfall[region], by, m) for m in rain_months]
                    bt = [v for v in bt if not np.isnan(v)]
                    if len(bt) == len(rain_months):
                        baseline.append(sum(bt))

                if len(baseline) < 10:
                    continue

                bl_mean = np.mean(baseline)
                bl_std  = np.std(baseline)
                spi     = (total - bl_mean) / bl_std if bl_std > 0 else 0

                p33    = np.percentile(baseline, 33)
                p67    = np.percentile(baseline, 67)
                target = 0 if total <= p33 else 1 if total <= p67 else 2

                spi_lag = np.nanmean([get_val(rainfall[region], year, m) for m in lag_months])

                rows.append({
                    'region':            region,
                    'year':              year,
                    'season':            season_name,
                    'enso_lag1':         enso1, 'iod_lag1':  iod1,
                    'enso_lag2':         enso2, 'iod_lag2':  iod2,
                    'enso_lag3':         enso3, 'iod_lag3':  iod3,
                    'enso_3mo_mean':     enso_mean,
                    'iod_3mo_mean':      iod_mean,
                    'pdo_lag1':          pdo1,  'pdo_lag2':  pdo2, 'pdo_lag3': pdo3,
                    'pdo_3mo_mean':      pdo_mean,
                    'atlantic_lag1':     atl1,  'atlantic_lag2': atl2, 'atlantic_lag3': atl3,
                    'atlantic_3mo_mean': atl_mean,
                    'spi_lag3':          spi_lag,
                    'spi':               spi,
                    'target':            target,
                    'total_rain_mm':     total,
                })

    out = pd.DataFrame(rows)
    out_path = f'{BASE_DIR}/data/processed/seasonal_4seasons.parquet'
    out.to_parquet(out_path, index=False)

    print(f"Saved {len(out)} rows to {out_path}")
    print(f"\nRows per season:\n{out['season'].value_counts()}")
    print(f"\nTarget distribution:\n{out.groupby(['season','target']).size().unstack()}")
    return out

if __name__ == '__main__':
    build_dataset()
