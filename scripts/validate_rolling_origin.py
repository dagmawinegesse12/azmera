"""
Azmera — Rolling-Origin Validation (Phase D / Phase E / Phase F)
================================================================
Runs rolling-origin (train 1981–T, forecast T+1, T from 1995→2021) for
model variants, separately for Kiremt and Belg:

── KIREMT (Phase D, 4-way comparison) ──────────────────────────────────────
  LEAN      — Phase B lean per-region features (enso/pdo/atlantic lags ± iod)
  LEAN+ANT  — lean + belg_antecedent_anom_z (Phase C: antecedent ALL Kiremt)
  ANT-ONLY  — belg_antecedent_anom_z alone (simple persistence baseline)
  PHASE D   — region-specific antecedent:
                lean+ant for {amhara, benishangul_gumz, gambela, harari, somali}
                lean-only for the remaining 8 Kiremt regions

── BELG (Phase E + F, 5+1 way comparison) ───────────────────────────────────
  Phase E (5-way, same feature set for all regions):
    BASELINE  — Phase D Belg features: atlantic_lag1/2, enso_lag1, iod_lag1, pdo_lag1
    AMM2      — BASELINE + amm_sst_jan  (January AMM of forecast year, ✓ safe)
    AMM23     — BASELINE + amm_sst_jan + amm_sst_dec  (Jan + Dec prior yr, ✓ safe)
    AMM-ONLY  — amm_sst_jan + amm_sst_dec only
    [amm_lag1 = February AMM — EXCLUDED: published ~Mar 15, after late-Feb issuance]

  Phase F (region-specific AMM, analogous to Phase D for Kiremt antecedent):
    PHASE F   — per-region choice: AMM2 for BELG_AMM_INCLUDE, BASELINE elsewhere
    BELG_AMM_INCLUDE = {addis_ababa, benishangul_gumz, dire_dawa, gambela,
                        harari, oromia, tigray}  (7 regions where AMM2 > BASELINE)
    BELG_AMM_EXCLUDE = {afar, amhara, sidama, snnpr, somali, south_west}  (6 regions)

AMM operational realism (Belg issued late February):
  amm_sst_jan  = January AMM (published ~Feb 15) ✓ SAFE
  amm_sst_dec  = December AMM of prior year (published ~Jan 15) ✓ SAFE
  amm_sst_feb  = February AMM (published ~Mar 15) ✗ NOT SAFE — excluded

AMM source:
  NOAA PSL https://psl.noaa.gov/data/correlation/amm.data
  Original: Vimont & Kossin, https://www.aos.wisc.edu/dvimont/MModes/Data.html
  Units: weighted SST anomaly amplitude (°C × EOF weight), range ≈ −7 to +8
  DISTINCT from atlantic_sst (= AMO): AMO is multi-decadal basin-wide;
  AMM is interannual tropical dipole, ENSO-residual, primary ITCZ driver.

Primary decision metric: rolling-origin HSS (prospective, no future-data leakage).
LOOCV HSS is reported separately for reference (not used for go/no-go decisions).

Outputs:
  Console: per-region and aggregate tables + verdicts for each season
  data/rolling_origin_results.csv: Kiremt Phase D + Belg Phase E + Phase F results
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
import os

DATA_PATH       = "data/processed/seasonal_enriched.parquet"
ANTECEDENT_PATH = "data/chirps_belg_historical.csv"
AMM_PATH        = "data/raw/amm_index.csv"

FIRST_TEST_YR = 1995   # minimum training window: 1981–1994 = 14 years
LAST_TEST_YR  = 2021   # keep 2022 out (recent; parquet may have incomplete SPI)


# ── Kiremt Phase D feature sets ────────────────────────────────────────────────

KIREMT_BASE_LEAN = ["enso_lag1", "enso_lag2", "pdo_lag1", "pdo_lag2", "atlantic_lag1"]
KIREMT_IOD_IN    = {"amhara", "benishangul_gumz", "somali"}
BELG_BASELINE    = ["atlantic_lag1", "atlantic_lag2", "enso_lag1", "iod_lag1", "pdo_lag1"]

# Kiremt antecedent feature
ANTECEDENT_FEAT = "belg_antecedent_anom_z"

# Phase D: Kiremt regions where Phase C rolling-origin showed Δ > +0.020
# amhara (+0.087), benishangul_gumz (+0.100), gambela (+0.055),
# harari (+0.078), somali (+0.210).
KIREMT_ANTECEDENT_INCLUDE = {"amhara", "benishangul_gumz", "gambela", "harari", "somali"}

# Phase E: AMM feature names
AMM_JAN = "amm_sst_jan"   # January of forecast year     (lag2, safe ✓)
AMM_DEC = "amm_sst_dec"   # December of prior year       (lag3, safe ✓)

# Phase E Belg variants (uniform feature set across all regions)
BELG_VARIANTS = {
    "BASELINE": BELG_BASELINE,
    "AMM2":     BELG_BASELINE + [AMM_JAN],
    "AMM23":    BELG_BASELINE + [AMM_JAN, AMM_DEC],
    "AMM-ONLY": [AMM_JAN, AMM_DEC],
}

# Phase F: region-specific AMM (analogous to Phase D for Kiremt antecedent)
# Regions where Phase E rolling-origin AMM2 HSS > BASELINE HSS → use AMM2.
# Decision made on Phase E rolling-origin HSS (prospective, no leakage).
# Δ values: addis_ababa (+0.143), benishangul_gumz (+0.006), dire_dawa (+0.117),
#           gambela (+0.214), harari (+0.117), oromia (+0.012), tigray (+0.123).
# Excluded: afar (-0.071), amhara (-0.039), sidama (-0.064),
#           snnpr (-0.020), somali (-0.151), south_west (-0.017).
BELG_AMM_INCLUDE = {
    "addis_ababa", "benishangul_gumz", "dire_dawa", "gambela",
    "harari", "oromia", "tigray",
}

AMM_FEATURES = {AMM_JAN, AMM_DEC}   # set of column names requiring injection


# ── Kiremt feature selectors ───────────────────────────────────────────────────

def get_lean_features(region, season):
    if season == "Kiremt":
        feats = list(KIREMT_BASE_LEAN)
        if region in KIREMT_IOD_IN:
            feats.append("iod_lag1")
        return feats
    return list(BELG_BASELINE)


def get_antecedent_features(region, season):
    """Lean + antecedent for Kiremt; same as lean for Belg."""
    base = get_lean_features(region, season)
    if season == "Kiremt":
        return base + [ANTECEDENT_FEAT]
    return base


def get_antecedent_only_features(season):
    if season == "Kiremt":
        return [ANTECEDENT_FEAT]
    return []


def get_phase_d_features(region, season):
    """Phase D: region-specific antecedent for Kiremt. Belg = lean."""
    base = get_lean_features(region, season)
    if season == "Kiremt" and region in KIREMT_ANTECEDENT_INCLUDE:
        return base + [ANTECEDENT_FEAT]
    return base


def get_phase_f_belg_features(region):
    """Phase F: region-specific AMM for Belg.
    AMM2 (BASELINE + amm_sst_jan) for BELG_AMM_INCLUDE;
    BASELINE for all other Belg regions.
    """
    if region in BELG_AMM_INCLUDE:
        return list(BELG_BASELINE) + [AMM_JAN]
    return list(BELG_BASELINE)


# ── Lookup loaders ─────────────────────────────────────────────────────────────

def load_antecedent_lookup():
    """Return {(region, year): z-score} for belg_antecedent_anom_z."""
    if not os.path.exists(ANTECEDENT_PATH):
        print(f"WARNING: {ANTECEDENT_PATH} not found — antecedent variants use 0.0",
              flush=True)
        return {}
    df = pd.read_csv(ANTECEDENT_PATH)
    return {
        (row["region"], int(row["year"])): float(row[ANTECEDENT_FEAT])
        for _, row in df.iterrows()
        if pd.notna(row[ANTECEDENT_FEAT])
    }


def load_amm_lookups():
    """
    Return {amm_col_name: {forecast_year: value}} for operationally safe AMM lags.

    amm_sst_jan[Y] = January Y AMM  (safe for late-Feb Belg issuance)
    amm_sst_dec[Y] = December Y-1 AMM (safe for late-Feb Belg issuance)
    """
    if not os.path.exists(AMM_PATH):
        print(f"WARNING: {AMM_PATH} not found — AMM features will use 0.0 fallback.\n"
              f"  Run: python scripts/download_amm_index.py", flush=True)
        return {AMM_JAN: {}, AMM_DEC: {}}

    amm  = pd.read_csv(AMM_PATH, parse_dates=["date"])
    jan  = {}
    dec  = {}
    for _, row in amm.iterrows():
        yr  = row["date"].year
        mo  = row["date"].month
        val = row["amm_sst"]
        if pd.isna(val):
            continue
        if mo == 1:
            jan[yr]     = val    # Jan Y → forecast year Y
        elif mo == 12:
            dec[yr + 1] = val    # Dec Y → forecast year Y+1
    return {AMM_JAN: jan, AMM_DEC: dec}


# ── Core rolling-origin ────────────────────────────────────────────────────────

def _compute_hss(y_true, y_pred):
    """Heidke Skill Score for 3-class problem."""
    if len(y_true) == 0:
        return np.nan
    cm = np.zeros((3, 3), dtype=int)
    for yt, yp in zip(y_true, y_pred):
        cm[int(yt), int(yp)] += 1
    n = cm.sum()
    if n == 0:
        return np.nan
    correct  = np.diag(cm).sum()
    expected = sum(cm[i, :].sum() * cm[:, i].sum() for i in range(3)) / n
    denom    = n - expected
    return float((correct - expected) / denom) if denom != 0 else 0.0


def rolling_origin_single(slice_df, feature_cols,
                          antecedent_lookup=None, amm_lookups=None):
    """
    Rolling-origin for one (region, season) slice.

    Feature injection:
      belg_antecedent_anom_z — from antecedent_lookup {(region, year): z}
      amm_sst_jan / amm_sst_dec — from amm_lookups {col: {year: val}}

    Core non-injected features: rows with NaN are dropped.
    Injected features: NaN filled with 0.0 (climatological neutral).

    Returns (y_true array, y_pred array) for all test years.
    """
    antecedent_lookup = antecedent_lookup or {}
    amm_lookups       = amm_lookups       or {}
    slice_df          = slice_df.copy().sort_values("year")

    # Inject antecedent if needed and not already present
    if ANTECEDENT_FEAT in feature_cols and ANTECEDENT_FEAT not in slice_df.columns:
        region = slice_df["region"].iloc[0]
        slice_df[ANTECEDENT_FEAT] = slice_df["year"].apply(
            lambda y: antecedent_lookup.get((region, int(y)), 0.0)
        )

    # Inject AMM features if needed
    for amm_col in AMM_FEATURES:
        if amm_col in feature_cols and amm_col not in slice_df.columns:
            lk = amm_lookups.get(amm_col, {})
            slice_df[amm_col] = slice_df["year"].apply(
                lambda y, lk=lk: lk.get(int(y), np.nan)
            )

    avail = [c for c in feature_cols if c in slice_df.columns]
    if not avail:
        return np.array([]), np.array([])

    # Drop rows where core (non-injected) features or target are missing
    injected_cols = {ANTECEDENT_FEAT} | AMM_FEATURES
    core_cols     = [c for c in avail if c not in injected_cols]
    slice_df      = slice_df.dropna(subset=["target"] + core_cols)

    # Fill remaining NaN in injected cols with 0.0
    slice_df[avail] = slice_df[avail].fillna(0.0)

    X_all   = slice_df[avail].values.copy()
    y_all   = slice_df["target"].values.astype(int)
    yrs_all = slice_df["year"].values

    y_true_out, y_pred_out = [], []
    for test_yr in range(FIRST_TEST_YR, LAST_TEST_YR + 1):
        train_mask = yrs_all < test_yr
        test_mask  = yrs_all == test_yr
        if train_mask.sum() < 10 or test_mask.sum() == 0:
            continue
        if len(np.unique(y_all[train_mask])) < 2:
            continue
        m = LogisticRegression(
            C=0.5, max_iter=1000, class_weight="balanced",
            solver="lbfgs", random_state=42,
        )
        m.fit(X_all[train_mask], y_all[train_mask])
        y_true_out.extend(y_all[test_mask])
        y_pred_out.extend(m.predict(X_all[test_mask]))

    return np.array(y_true_out), np.array(y_pred_out)


# ── Main comparison ────────────────────────────────────────────────────────────

def run_comparison():
    print("Loading data …", flush=True)
    df  = pd.read_parquet(DATA_PATH)
    ant = load_antecedent_lookup()
    amm = load_amm_lookups()
    print(f"  Antecedent lookup: {len(ant)} (region, year) entries", flush=True)
    print(f"  AMM Jan lookup:    {len(amm[AMM_JAN])} years", flush=True)
    print(f"  AMM Dec lookup:    {len(amm[AMM_DEC])} years", flush=True)

    regions = sorted(df["region"].unique())
    records = []

    # ── KIREMT: Phase D 4-way comparison ──────────────────────────────────────
    season = "Kiremt"
    yt_lean_all,  yp_lean_all  = [], []
    yt_ant_all,   yp_ant_all   = [], []
    yt_aonly_all, yp_aonly_all = [], []
    yt_d_all,     yp_d_all     = [], []

    for region in regions:
        slice_df = df[(df["region"] == region) & (df["season"] == season)].copy()

        lean_cols  = get_lean_features(region, season)
        ant_cols   = get_antecedent_features(region, season)
        aonly_cols = get_antecedent_only_features(season)
        d_cols     = get_phase_d_features(region, season)

        yt_l, yp_l   = rolling_origin_single(slice_df, lean_cols,  ant)
        yt_a, yp_a   = rolling_origin_single(slice_df, ant_cols,   ant)
        yt_d, yp_d   = rolling_origin_single(slice_df, d_cols,     ant)

        if aonly_cols:
            yt_ao, yp_ao = rolling_origin_single(slice_df, aonly_cols, ant)
            hss_aonly    = _compute_hss(yt_ao, yp_ao) if len(yt_ao) >= 5 else np.nan
        else:
            yt_ao, yp_ao = np.array([]), np.array([])
            hss_aonly    = np.nan

        hss_lean = _compute_hss(yt_l, yp_l) if len(yt_l) >= 5 else np.nan
        hss_ant  = _compute_hss(yt_a, yp_a) if len(yt_a) >= 5 else np.nan
        hss_d    = _compute_hss(yt_d, yp_d) if len(yt_d) >= 5 else np.nan

        def _delta(a, b):
            return round(a - b, 3) if not (np.isnan(a) or np.isnan(b)) else np.nan

        records.append({
            "season":         season,
            "region":         region,
            "n_test":         len(yt_l),
            "hss_lean":       round(hss_lean,  3) if not np.isnan(hss_lean)  else np.nan,
            "hss_ant":        round(hss_ant,   3) if not np.isnan(hss_ant)   else np.nan,
            "hss_aonly":      round(hss_aonly, 3) if not np.isnan(hss_aonly) else np.nan,
            "hss_d":          round(hss_d,     3) if not np.isnan(hss_d)     else np.nan,
            "delta_ant":      _delta(hss_ant,   hss_lean),
            "delta_aonly":    _delta(hss_aonly, hss_lean),
            "delta_d_vs_b":   _delta(hss_d,    hss_lean),
            "delta_d_vs_c":   _delta(hss_d,    hss_ant),
            "lean_features":  str(lean_cols),
            "ant_features":   str(ant_cols),
            "d_features":     str(d_cols),
        })

        yt_lean_all.extend(yt_l);  yp_lean_all.extend(yp_l)
        yt_ant_all.extend(yt_a);   yp_ant_all.extend(yp_a)
        yt_d_all.extend(yt_d);     yp_d_all.extend(yp_d)
        if len(yt_ao) > 0:
            yt_aonly_all.extend(yt_ao); yp_aonly_all.extend(yp_ao)

    # Kiremt aggregate
    agg_lean  = _compute_hss(np.array(yt_lean_all), np.array(yp_lean_all))
    agg_ant   = _compute_hss(np.array(yt_ant_all),  np.array(yp_ant_all))
    agg_d     = _compute_hss(np.array(yt_d_all),    np.array(yp_d_all))
    agg_aonly = (_compute_hss(np.array(yt_aonly_all), np.array(yp_aonly_all))
                 if yt_aonly_all else np.nan)
    records.append({
        "season":        season,
        "region":        "AGGREGATE",
        "n_test":        len(yt_lean_all),
        "hss_lean":      round(agg_lean,  4),
        "hss_ant":       round(agg_ant,   4),
        "hss_aonly":     round(agg_aonly, 4) if not np.isnan(agg_aonly) else np.nan,
        "hss_d":         round(agg_d,     4),
        "delta_ant":     round(agg_ant   - agg_lean, 4),
        "delta_aonly":   round(agg_aonly - agg_lean, 4) if not np.isnan(agg_aonly) else np.nan,
        "delta_d_vs_b":  round(agg_d - agg_lean, 4),
        "delta_d_vs_c":  round(agg_d - agg_ant,  4),
        "lean_features": "—",
        "ant_features":  "—",
        "d_features":    "—",
    })

    # ── BELG: Phase E (5-way) + Phase F (region-specific AMM) ────────────────
    season = "Belg"
    pooled     = {vname: ([], []) for vname in BELG_VARIANTS}
    pf_yt_all  = []   # Phase F pooled predictions (re-use Phase E runs)
    pf_yp_all  = []
    per_region_belg = {}   # {region: {vname: (yt, yp)}} — for Phase F re-pooling

    for region in regions:
        slice_df = df[(df["region"] == region) & (df["season"] == season)].copy()
        row_rec  = {
            "season": season,
            "region": region,
            "n_test": None,
        }
        per_region_belg[region] = {}

        for vname, feat_cols in BELG_VARIANTS.items():
            yt, yp = rolling_origin_single(
                slice_df, feat_cols,
                antecedent_lookup=ant, amm_lookups=amm,
            )
            hss = _compute_hss(yt, yp) if len(yt) >= 5 else np.nan
            key = f"hss_{vname.lower().replace('-', '_')}"
            row_rec[key] = round(hss, 3) if not np.isnan(hss) else np.nan
            row_rec[f"features_{vname.lower().replace('-','_')}"] = str(feat_cols)
            if row_rec["n_test"] is None:
                row_rec["n_test"] = len(yt)
            pooled[vname][0].extend(yt)
            pooled[vname][1].extend(yp)
            per_region_belg[region][vname] = (yt, yp)

        # Delta columns vs BASELINE
        base_hss = row_rec.get("hss_baseline", np.nan)
        for vname in BELG_VARIANTS:
            if vname == "BASELINE":
                continue
            vhss  = row_rec.get(f"hss_{vname.lower().replace('-','_')}", np.nan)
            delta = round(vhss - base_hss, 3) if not (pd.isna(vhss) or pd.isna(base_hss)) else np.nan
            row_rec[f"delta_{vname.lower().replace('-','_')}_vs_base"] = delta

        # Phase F: pick per-region winner (AMM2 if in BELG_AMM_INCLUDE, else BASELINE)
        # Re-uses already-computed Phase E predictions — no extra rolling-origin runs.
        if region in BELG_AMM_INCLUDE:
            pf_yt, pf_yp = per_region_belg[region]["AMM2"]
            row_rec["phase_f_choice"] = "AMM2"
        else:
            pf_yt, pf_yp = per_region_belg[region]["BASELINE"]
            row_rec["phase_f_choice"] = "BASELINE"
        pf_hss = _compute_hss(pf_yt, pf_yp) if len(pf_yt) >= 5 else np.nan
        row_rec["hss_phase_f"] = round(pf_hss, 3) if not np.isnan(pf_hss) else np.nan
        row_rec["delta_phase_f_vs_base"] = (
            round(pf_hss - base_hss, 3)
            if not (pd.isna(pf_hss) or pd.isna(base_hss)) else np.nan
        )
        row_rec["pf_features"] = str(get_phase_f_belg_features(region))
        pf_yt_all.extend(pf_yt)
        pf_yp_all.extend(pf_yp)

        records.append(row_rec)

    # ── Belg aggregate ────────────────────────────────────────────────────────
    agg_rec = {"season": season, "region": "AGGREGATE", "n_test": None}
    base_agg_hss = None
    for vname in BELG_VARIANTS:
        pt, pp   = pooled[vname]
        agg_hss  = _compute_hss(np.array(pt), np.array(pp)) if pt else np.nan
        key      = f"hss_{vname.lower().replace('-','_')}"
        agg_rec[key] = round(agg_hss, 4) if not np.isnan(agg_hss) else np.nan
        agg_rec[f"features_{vname.lower().replace('-','_')}"] = "—"
        if agg_rec["n_test"] is None:
            agg_rec["n_test"] = len(pt)
        if vname == "BASELINE":
            base_agg_hss = agg_hss

    for vname in BELG_VARIANTS:
        if vname == "BASELINE":
            continue
        vhss  = agg_rec.get(f"hss_{vname.lower().replace('-','_')}", np.nan)
        delta = round(vhss - base_agg_hss, 4) if not (pd.isna(vhss) or base_agg_hss is None) else np.nan
        agg_rec[f"delta_{vname.lower().replace('-','_')}_vs_base"] = delta

    # Phase F aggregate
    pf_agg_hss = _compute_hss(np.array(pf_yt_all), np.array(pf_yp_all)) if pf_yt_all else np.nan
    agg_rec["hss_phase_f"] = round(pf_agg_hss, 4) if not np.isnan(pf_agg_hss) else np.nan
    agg_rec["delta_phase_f_vs_base"] = (
        round(pf_agg_hss - base_agg_hss, 4)
        if not (np.isnan(pf_agg_hss) or base_agg_hss is None) else np.nan
    )
    agg_rec["phase_f_choice"] = "—"
    agg_rec["pf_features"] = "—"

    records.append(agg_rec)

    return pd.DataFrame(records)


# ── Pretty printer ─────────────────────────────────────────────────────────────

def _fmt(val, width=8, decimals=3):
    if pd.isna(val):
        return f"{'N/A':>{width}}"
    return f"{val:>+{width}.{decimals}f}"


def _direction(delta, threshold=0.005):
    if pd.isna(delta):      return " "
    if delta >  threshold:  return "▲"
    if delta < -threshold:  return "▼"
    return "="


def print_report(df):
    # ── KIREMT: Phase D 4-way ─────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("PHASE D — KIREMT ROLLING-ORIGIN VALIDATION  (4-way comparison)")
    print("  LEAN:     Phase B lean per-region features (enso/pdo/atlantic lags ± iod)")
    print("  LEAN+ANT: Phase C — lean + belg_antecedent_anom_z (all Kiremt regions)")
    print("  ANT-ONLY: belg_antecedent_anom_z alone (simple persistence baseline)")
    print(f"  PHASE D:  region-specific — ant for {sorted(KIREMT_ANTECEDENT_INCLUDE)}")
    print(f"            lean-only for all other Kiremt regions")
    print(f"  Test window: {FIRST_TEST_YR}–{LAST_TEST_YR}  |  Decision metric: rolling-origin HSS")
    print("=" * 90)

    sdf      = df[df["season"] == "Kiremt"]
    reg_rows = sdf[sdf["region"] != "AGGREGATE"].sort_values("region")
    agg_row  = sdf[sdf["region"] == "AGGREGATE"].iloc[0]

    print(f"  {'Region':<22} {'n':>4}  {'PhaseB':>8}  {'PhaseC':>8}  {'PhaseD':>8}  "
          f"{'ΔD-B':>8}  {'ΔD-C':>8}  {'chosen'}  ")
    print(f"  {'─'*22} {'──':>4}  {'──────':>8}  {'──────':>8}  {'──────':>8}  "
          f"{'──────':>8}  {'──────':>8}  ──────────")

    for _, row in reg_rows.iterrows():
        db = _direction(row["delta_d_vs_b"])
        dc = _direction(row["delta_d_vs_c"])
        chosen = "lean+ant" if row["region"] in KIREMT_ANTECEDENT_INCLUDE else "lean"
        print(
            f"  {row['region']:<22} {row['n_test']:>4}  "
            f"{_fmt(row['hss_lean'])}  "
            f"{_fmt(row['hss_ant'])}  "
            f"{_fmt(row['hss_d'])}  "
            f"{_fmt(row['delta_d_vs_b'])}{db} "
            f"{_fmt(row['delta_d_vs_c'])}{dc} "
            f"  {chosen}"
        )

    print(f"  {'─'*22} {'──':>4}  {'──────':>8}  {'──────':>8}  {'──────':>8}  "
          f"{'──────':>8}  {'──────':>8}")
    db = _direction(agg_row["delta_d_vs_b"])
    dc = _direction(agg_row["delta_d_vs_c"])
    print(
        f"  {'AGGREGATE':<22} {agg_row['n_test']:>4}  "
        f"{_fmt(agg_row['hss_lean'], 8, 4)}  "
        f"{_fmt(agg_row['hss_ant'],  8, 4)}  "
        f"{_fmt(agg_row['hss_d'],    8, 4)}  "
        f"{_fmt(agg_row['delta_d_vs_b'], 8, 4)}{db} "
        f"{_fmt(agg_row['delta_d_vs_c'], 8, 4)}{dc}"
    )

    # Kiremt verdict
    print(f"\n  KIREMT VERDICT:")
    k_agg = agg_row
    print(f"    Phase B (lean):     {k_agg['hss_lean']:+.4f}")
    print(f"    Phase C (lean+ant): {k_agg['hss_ant']:+.4f}")
    print(f"    Phase D (mixed):    {k_agg['hss_d']:+.4f}  "
          f"(ΔD-B={k_agg['delta_d_vs_b']:+.4f}, ΔD-C={k_agg['delta_d_vs_c']:+.4f})")
    ddc = k_agg["delta_d_vs_c"]
    if ddc > 0.005:
        print(f"    → ✅ Phase D > Phase C — regional selection improves aggregate")
    elif ddc < -0.005:
        print(f"    → ❌ Phase D < Phase C — regression")
    else:
        print(f"    → ⚠️  Phase D ≈ Phase C (|Δ| < 0.005)")

    # ── BELG: Phase E (5-way) + Phase F (region-specific AMM) ───────────────
    vnames = list(BELG_VARIANTS.keys())

    print("\n\n" + "=" * 110)
    print("PHASE E — BELG AMM EXPERIMENT  (rolling-origin HSS, 5-way comparison)")
    print("  BASELINE : Phase D Belg: atlantic_lag1/2, enso_lag1, iod_lag1, pdo_lag1")
    print("  AMM2     : BASELINE + amm_sst_jan  (January AMM, published ~Feb 15 ✓ safe)")
    print("  AMM23    : BASELINE + amm_sst_jan + amm_sst_dec  (Jan + Dec prior yr ✓ safe)")
    print("  AMM-ONLY : amm_sst_jan + amm_sst_dec  (AMM predictors only)")
    print("  [amm_lag1 = February AMM — EXCLUDED: published ~Mar 15, after issuance ✗]")
    print(f"  AMM source: NOAA PSL https://psl.noaa.gov/data/correlation/amm.data")
    print(f"  Test window: {FIRST_TEST_YR}–{LAST_TEST_YR}  |  Decision metric: rolling-origin HSS")
    print("=" * 110)

    bdf      = df[df["season"] == "Belg"]
    breg     = bdf[bdf["region"] != "AGGREGATE"].sort_values("region")
    bagg_row = bdf[bdf["region"] == "AGGREGATE"].iloc[0]

    # Header: Phase D, Phase E (AMM2 only, for clarity), Phase F
    print(f"  {'Region':<22} {'n':>4}  {'PhaseD':>8}  {'E:AMM2':>8}  {'PhaseF':>8}  "
          f"{'ΔE-D':>8}  {'ΔF-D':>8}  {'ΔF-E':>8}  {'F choice'}")
    print(f"  {'─'*22} {'──':>4}  {'──────':>8}  {'──────':>8}  {'──────':>8}  "
          f"{'──────':>8}  {'──────':>8}  {'──────':>8}  ────────")

    for _, row in breg.iterrows():
        base_hss  = row.get("hss_baseline",  np.nan)
        amm2_hss  = row.get("hss_amm2",      np.nan)
        pf_hss    = row.get("hss_phase_f",   np.nan)
        delta_e   = row.get("delta_amm2_vs_base", np.nan)
        delta_f_d = row.get("delta_phase_f_vs_base", np.nan)
        delta_f_e = (round(pf_hss - amm2_hss, 3)
                     if not (pd.isna(pf_hss) or pd.isna(amm2_hss)) else np.nan)
        choice    = row.get("phase_f_choice", "—")
        print(
            f"  {row['region']:<22} {int(row['n_test']):>4}  "
            f"{_fmt(base_hss)}  {_fmt(amm2_hss)}  {_fmt(pf_hss)}  "
            f"{_fmt(delta_e)}{_direction(delta_e)} "
            f"{_fmt(delta_f_d)}{_direction(delta_f_d)} "
            f"{_fmt(delta_f_e)}{_direction(delta_f_e)} "
            f"  {choice}"
        )

    print(f"  {'─'*22} {'──':>4}  {'──────':>8}  {'──────':>8}  {'──────':>8}  "
          f"{'──────':>8}  {'──────':>8}  {'──────':>8}")

    base_agg  = bagg_row.get("hss_baseline",  np.nan)
    amm2_agg  = bagg_row.get("hss_amm2",      np.nan)
    pf_agg    = bagg_row.get("hss_phase_f",   np.nan)
    de_agg    = bagg_row.get("delta_amm2_vs_base", np.nan)
    df_d_agg  = bagg_row.get("delta_phase_f_vs_base", np.nan)
    df_e_agg  = (round(pf_agg - amm2_agg, 4)
                 if not (pd.isna(pf_agg) or pd.isna(amm2_agg)) else np.nan)
    print(
        f"  {'AGGREGATE':<22} {int(bagg_row['n_test']):>4}  "
        f"{_fmt(base_agg, 8, 4)}  {_fmt(amm2_agg, 8, 4)}  {_fmt(pf_agg, 8, 4)}  "
        f"{_fmt(de_agg, 8, 4)}{_direction(de_agg)} "
        f"{_fmt(df_d_agg, 8, 4)}{_direction(df_d_agg)} "
        f"{_fmt(df_e_agg, 8, 4)}{_direction(df_e_agg)}"
    )

    # Phase F regional breakdown
    print(f"\n{'─' * 110}")
    print("  PHASE F — BELG REGIONAL DECISIONS")
    print(f"  (AMM2 features for regions where Phase E rolling-origin AMM2 > BASELINE)")
    print(f"{'─' * 110}")

    amm_regions  = breg[breg["region"].isin(BELG_AMM_INCLUDE)].sort_values("region")
    base_regions = breg[~breg["region"].isin(BELG_AMM_INCLUDE)].sort_values("region")

    print(f"\n  Belg regions using AMM2 (Phase F = Phase E AMM2): {len(amm_regions)}")
    for _, r in amm_regions.iterrows():
        d = r.get("delta_amm2_vs_base", np.nan)
        flag = "▲" if (not pd.isna(d) and d > 0.005) else ("=" if not pd.isna(d) else " ")
        print(f"    {r['region']:<22}  D={r['hss_baseline']:+.3f}  E(AMM2)={r['hss_amm2']:+.3f}  "
              f"F={r['hss_phase_f']:+.3f}  ΔF-D={d:+.3f}{flag}")

    print(f"\n  Belg regions using BASELINE (dropped AMM vs Phase E): {len(base_regions)}")
    for _, r in base_regions.iterrows():
        d = r.get("delta_amm2_vs_base", np.nan)
        flag = "▼" if (not pd.isna(d) and d < -0.005) else ("=" if not pd.isna(d) else " ")
        print(f"    {r['region']:<22}  D={r['hss_baseline']:+.3f}  E(AMM2)={r['hss_amm2']:+.3f}  "
              f"F={r['hss_phase_f']:+.3f}  ΔF-D={r.get('delta_phase_f_vs_base', np.nan):+.3f}{flag}")

    # Verdict
    print(f"\n{'=' * 110}")
    print("PHASE E / PHASE F VERDICT")
    print("=" * 110)
    print(f"  Phase D (Belg baseline):   {base_agg:+.4f}")
    print(f"  Phase E AMM2 (uniform):    {amm2_agg:+.4f}  (ΔE-D = {de_agg:+.4f})")
    print(f"  Phase F (region-specific): {pf_agg:+.4f}  (ΔF-D = {df_d_agg:+.4f}, ΔF-E = {df_e_agg:+.4f})")
    print()

    def _verdict(delta, label):
        if pd.isna(delta):      return f"⚠️  {label} N/A"
        if delta > 0.005:       return f"✅ KEEP — Δ = {delta:+.4f} > +0.005"
        if delta <= 0.0:        return f"❌ REVERT — Δ = {delta:+.4f} ≤ 0.000"
        return f"⚠️  MARGINAL — Δ = {delta:+.4f}, in 0.000–0.005 band"

    print(f"  Phase E AMM2: {_verdict(de_agg, 'AMM2')}")
    print(f"  Phase F:      {_verdict(df_d_agg, 'Phase F')}")
    print()

    if not pd.isna(df_d_agg) and df_d_agg > 0.005:
        print(f"  ★ Phase F ACCEPTED — region-specific AMM2 improves aggregate Belg by {df_d_agg:+.4f}")
        print(f"    AMM2 features used for: {sorted(BELG_AMM_INCLUDE)}")
        print(f"    BASELINE for: {sorted(set(breg['region'].tolist()) - BELG_AMM_INCLUDE)}")
        print(f"    Next: update build_region_models.py and retrain 13 Belg models.")
    elif not pd.isna(df_d_agg) and df_d_agg <= 0.0:
        print(f"  ✗ Phase F REJECTED — no aggregate improvement. Revert to Phase D Belg.")
    else:
        print(f"  ⚠️  Phase F MARGINAL — Δ in 0.000–0.005 band. Use judgement.")
    print("=" * 110)


if __name__ == "__main__":
    results = run_comparison()
    print_report(results)
    out_path = "data/rolling_origin_results.csv"
    results.to_csv(out_path, index=False)
    print(f"\nFull results saved: {out_path}")
