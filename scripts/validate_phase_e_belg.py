"""
Azmera — Phase E: AMM Experiment for Belg Season
=================================================
Tests Atlantic Meridional Mode (AMM) SST features in the Belg model.

Operational context:
  Belg season: March–May. Forecast issued late February / early March.
  amm_sst_jan  = January AMM of forecast year Y  (NOAA publishes ~Feb 15) ✓ SAFE
  amm_sst_dec  = December AMM of year Y-1         (NOAA publishes ~Jan 15) ✓ SAFE
  amm_sst_feb  = February AMM of forecast year Y  (NOAA publishes ~Mar 15) ✗ NOT SAFE

AMM vs AMO:
  Current model already uses atlantic_sst (= AMO, Atlantic Multidecadal Oscillation):
    - Basin-wide multi-decadal signal, lag-1 autocorr ≈ 0.929
    - ENSO correlation ≈ 0.05 (near-zero)
  AMM is a DISTINCT index:
    - Tropical Atlantic dipole (interannual, 1–5 yr), ENSO-residual
    - Primary ITCZ position driver
    - AMM + AMO = genuinely orthogonal predictors

Five Belg variants (amm_lag1 excluded — NOT operationally safe):
  BASELINE   — Phase D Belg features: atlantic_lag1/2, enso_lag1, iod_lag1, pdo_lag1
  AMM2       — BASELINE + amm_sst_jan
  AMM23      — BASELINE + amm_sst_jan + amm_sst_dec
  AMM-ONLY   — amm_sst_jan + amm_sst_dec  (AMM predictors only, no SST indices)
  [amm_lag1 = February AMM — EXCLUDED: published after late-February issuance]

Decision rule:
  KEEP   if aggregate Belg rolling-origin HSS Δ > +0.005 vs BASELINE
  REVERT if Δ ≤ 0.000
  Do NOT call LOOCV-only improvement a success.

Outputs:
  Console: per-region and aggregate table for all 5 Belg variants + verdict
  data/rolling_origin_phase_e_belg.csv: full per-region results
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
import os

DATA_PATH  = "data/processed/seasonal_enriched.parquet"
AMM_PATH   = "data/raw/amm_index.csv"
OUT_PATH   = "data/rolling_origin_phase_e_belg.csv"

FIRST_TEST_YR = 1995
LAST_TEST_YR  = 2021

# Phase D Belg baseline features (= lean, unchanged from Phase D)
BELG_BASELINE = [
    "atlantic_lag1", "atlantic_lag2",
    "enso_lag1",
    "iod_lag1",
    "pdo_lag1",
]

# AMM feature names for operationally safe lags
AMM_JAN = "amm_sst_jan"   # January of forecast year (lag2)
AMM_DEC = "amm_sst_dec"   # December of prior year  (lag3)

# Phase E Belg variants
VARIANTS = {
    "BASELINE": BELG_BASELINE,
    "AMM2":     BELG_BASELINE + [AMM_JAN],
    "AMM23":    BELG_BASELINE + [AMM_JAN, AMM_DEC],
    "AMM-ONLY": [AMM_JAN, AMM_DEC],
}


# ── AMM lookup builder ─────────────────────────────────────────────────────────

def load_amm_lookups(path: str) -> dict:
    """
    Build per-year lookups for AMM features.

    Returns:
        {
          "amm_sst_jan": {year: value},  # January of year Y → forecast year Y
          "amm_sst_dec": {year: value},  # December of Y-1  → forecast year Y
        }
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"AMM index not found: {path}\n"
            "Run: python scripts/download_amm_index.py"
        )
    amm = pd.read_csv(path, parse_dates=["date"])
    jan_lookup = {}
    dec_lookup = {}
    for _, row in amm.iterrows():
        yr  = row["date"].year
        mo  = row["date"].month
        val = row["amm_sst"]
        if pd.isna(val):
            continue
        if mo == 1:
            jan_lookup[yr] = val         # Jan Y → used for Belg forecast year Y
        elif mo == 12:
            dec_lookup[yr + 1] = val     # Dec Y → used for Belg forecast year Y+1
    print(f"  AMM Jan lookup: {len(jan_lookup)} years  "
          f"({min(jan_lookup)} – {max(jan_lookup)})")
    print(f"  AMM Dec lookup: {len(dec_lookup)} years  "
          f"({min(dec_lookup)} – {max(dec_lookup)})")
    return {AMM_JAN: jan_lookup, AMM_DEC: dec_lookup}


# ── HSS ───────────────────────────────────────────────────────────────────────

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


# ── Rolling-origin ─────────────────────────────────────────────────────────────

def rolling_origin_belg(slice_df: pd.DataFrame,
                        feature_cols: list[str],
                        amm_lookups: dict) -> tuple[np.ndarray, np.ndarray]:
    """
    Rolling-origin for one (region, Belg) slice with AMM feature injection.

    AMM features (amm_sst_jan, amm_sst_dec) are injected from the pre-built
    lookup dicts — they are NOT stored in seasonal_enriched.parquet.
    Non-AMM features come directly from the parquet.

    Fallback for missing AMM values: 0.0 (climatological neutral).
    Core non-AMM features: rows with NaN are dropped (no fallback).
    """
    slice_df = slice_df.copy().sort_values("year")

    # Inject AMM columns
    amm_cols = [c for c in feature_cols if c in amm_lookups]
    for col in amm_cols:
        lk = amm_lookups[col]
        slice_df[col] = slice_df["year"].apply(lambda y: lk.get(int(y), np.nan))

    # Drop rows where core (non-AMM) features or target are missing
    core_cols = [c for c in feature_cols if c not in amm_lookups]
    avail     = [c for c in feature_cols if c in slice_df.columns]
    if not avail:
        return np.array([]), np.array([])

    slice_df = slice_df.dropna(subset=["target"] + core_cols)

    # Fill any remaining NaN in AMM cols with 0.0 (neutral fallback)
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

def run_phase_e():
    print("Loading data …", flush=True)
    df         = pd.read_parquet(DATA_PATH)
    amm_lookups = load_amm_lookups(AMM_PATH)
    belg_df    = df[df["season"] == "Belg"].copy()

    regions = sorted(belg_df["region"].unique())
    records = []

    # Accumulate pooled predictions for aggregate HSS
    pooled = {vname: ([], []) for vname in VARIANTS}

    for region in regions:
        slice_df = belg_df[belg_df["region"] == region].copy()
        row_rec  = {"region": region, "n_test": None}

        for vname, feat_cols in VARIANTS.items():
            yt, yp = rolling_origin_belg(slice_df, feat_cols, amm_lookups)
            hss    = _compute_hss(yt, yp) if len(yt) >= 5 else np.nan
            row_rec[f"hss_{vname.lower().replace('-', '_')}"] = (
                round(hss, 3) if not np.isnan(hss) else np.nan
            )
            row_rec[f"features_{vname.lower().replace('-', '_')}"] = str(feat_cols)
            if row_rec["n_test"] is None:
                row_rec["n_test"] = len(yt)
            pt, pp = pooled[vname]
            pt.extend(yt)
            pp.extend(yp)

        records.append(row_rec)

    # ── Aggregate row ──────────────────────────────────────────────────────────
    agg_rec = {"region": "AGGREGATE", "n_test": None}
    for vname in VARIANTS:
        pt, pp = pooled[vname]
        agg_hss = _compute_hss(np.array(pt), np.array(pp)) if pt else np.nan
        key = f"hss_{vname.lower().replace('-', '_')}"
        agg_rec[key] = round(agg_hss, 4) if not np.isnan(agg_hss) else np.nan
        agg_rec[f"features_{vname.lower().replace('-', '_')}"] = "—"
        if agg_rec["n_test"] is None:
            agg_rec["n_test"] = len(pt)
    records.append(agg_rec)

    results_df = pd.DataFrame(records)

    # ── Add delta columns vs BASELINE ──────────────────────────────────────────
    for vname in VARIANTS:
        if vname == "BASELINE":
            continue
        key_base = "hss_baseline"
        key_v    = f"hss_{vname.lower().replace('-', '_')}"
        delta_k  = f"delta_{vname.lower().replace('-', '_')}_vs_base"
        results_df[delta_k] = results_df.apply(
            lambda r: round(r[key_v] - r[key_base], 3)
            if not (pd.isna(r[key_v]) or pd.isna(r[key_base])) else np.nan,
            axis=1,
        )

    return results_df


# ── Report ─────────────────────────────────────────────────────────────────────

def _fmt(val, w=8, d=3):
    if pd.isna(val):
        return f"{'—':>{w}}"
    return f"{val:>+{w}.{d}f}"


def _dir(delta, t=0.005):
    if pd.isna(delta):     return " "
    if delta >  t:         return "▲"
    if delta < -t:         return "▼"
    return "="


def print_report(df):
    vnames = list(VARIANTS.keys())

    print("\n" + "=" * 100)
    print("PHASE E — BELG AMM EXPERIMENT  (rolling-origin HSS, 5-way comparison)")
    print("  BASELINE : Phase D Belg features: atlantic_lag1/2, enso_lag1, iod_lag1, pdo_lag1")
    print("  AMM2     : BASELINE + amm_sst_jan  (January AMM, safe ✓)")
    print("  AMM23    : BASELINE + amm_sst_jan + amm_sst_dec  (Jan + Dec prior yr, safe ✓)")
    print("  AMM-ONLY : amm_sst_jan + amm_sst_dec  (AMM predictors only)")
    print("  [amm_lag1/Feb AMM excluded — published after late-Feb issuance ✗]")
    print(f"  AMM source: NOAA PSL https://psl.noaa.gov/data/correlation/amm.data")
    print(f"  Test window: {FIRST_TEST_YR}–{LAST_TEST_YR}  |  Decision metric: rolling-origin HSS")
    print("=" * 100)

    reg_rows = df[df["region"] != "AGGREGATE"].sort_values("region")
    agg_row  = df[df["region"] == "AGGREGATE"].iloc[0]

    hdr1 = f"  {'Region':<22} {'n':>4}"
    hdr2 = f"  {'─'*22} {'──':>4}"
    for v in vnames:
        hdr1 += f"  {'BASELINE' if v == 'BASELINE' else v:>10}"
        hdr2 += f"  {'──────────':>10}"
    for v in vnames:
        if v != "BASELINE":
            hdr1 += f"  {'Δ'+v:>10}"
            hdr2 += f"  {'──────────':>10}"
    print(hdr1)
    print(hdr2)

    for _, row in reg_rows.iterrows():
        line = f"  {row['region']:<22} {int(row['n_test']):>4}"
        for v in vnames:
            key = f"hss_{v.lower().replace('-','_')}"
            line += f"  {_fmt(row[key], 10, 3)}"
        for v in vnames:
            if v == "BASELINE":
                continue
            dkey = f"delta_{v.lower().replace('-','_')}_vs_base"
            dval = row.get(dkey, np.nan)
            line += f"  {_fmt(dval, 9, 3)}{_dir(dval)}"
        print(line)

    print(f"  {'─'*22} {'──':>4}" + "  ──────────" * len(vnames) +
          "  ─────────" * (len(vnames) - 1))

    # Aggregate
    agg_line = f"  {'AGGREGATE':<22} {int(agg_row['n_test']):>4}"
    for v in vnames:
        key = f"hss_{v.lower().replace('-','_')}"
        agg_line += f"  {_fmt(agg_row[key], 10, 4)}"
    for v in vnames:
        if v == "BASELINE":
            continue
        dkey = f"delta_{v.lower().replace('-','_')}_vs_base"
        dval = agg_row.get(dkey, np.nan)
        agg_line += f"  {_fmt(dval, 9, 4)}{_dir(dval)}"
    print(agg_line)

    # ── Verdict ────────────────────────────────────────────────────────────────
    base_hss = agg_row["hss_baseline"]
    print(f"\n{'=' * 100}")
    print("VERDICT  (decision rule: KEEP if aggregate rolling-origin Δ > +0.005 vs BASELINE)")
    print("=" * 100)
    print(f"  BASELINE aggregate Belg HSS: {base_hss:+.4f}")
    print()

    best_variant = None
    best_delta   = 0.0

    for v in vnames:
        if v == "BASELINE":
            continue
        dkey  = f"delta_{v.lower().replace('-','_')}_vs_base"
        dval  = agg_row.get(dkey, np.nan)
        vhss  = agg_row.get(f"hss_{v.lower().replace('-','_')}", np.nan)

        # Count per-region wins/losses
        wins   = 0
        losses = 0
        for _, r in reg_rows.iterrows():
            rd = r.get(dkey, np.nan)
            if pd.isna(rd):
                continue
            if rd > 0.005:
                wins   += 1
            elif rd < -0.005:
                losses += 1

        if pd.isna(dval):
            verdict = "⚠️  N/A"
        elif dval > 0.005:
            verdict = f"✅ KEEP — aggregate rolling-origin +{dval:+.4f} > +0.005"
            if best_variant is None or dval > best_delta:
                best_variant = v
                best_delta   = dval
        elif dval <= 0.0:
            verdict = f"❌ REVERT — Δ = {dval:+.4f} ≤ 0.000 (no improvement)"
        else:
            verdict = f"⚠️  MARGINAL — Δ = {dval:+.4f}, in 0.000–0.005 band (borderline)"

        print(f"  {v:<10}: HSS={vhss:+.4f}  Δ={dval:+.4f}  "
              f"regions ▲{wins}/▼{losses}")
        print(f"    → {verdict}")
        print()

    if best_variant:
        print(f"  ★ Best variant: {best_variant}  (Δ = {best_delta:+.4f})")
        print(f"    → If accepted: integrate {best_variant} features into "
              f"build_region_models.py Belg and retrain.")
    else:
        print(f"  ✗ No variant exceeded +0.005 threshold.")
        print(f"    → Phase D Belg features unchanged. AMM not added.")

    print("=" * 100)


if __name__ == "__main__":
    print("Phase E — Belg AMM Experiment")
    print("=" * 60)
    results = run_phase_e()
    print_report(results)
    results.to_csv(OUT_PATH, index=False)
    print(f"\nDetailed results saved: {OUT_PATH}")
