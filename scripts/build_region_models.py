"""
Azmera — Per-Region Model Training (Phase F)
=============================================
Trains separate Logistic Regression models for each Ethiopian region.
Replaces the single shared model (azmera_model_v3.pkl) with per-region models
that capture each region's unique ENSO/IOD/PDO/AMM relationship.
Run after data pipeline is complete.

Phase history (Kiremt):
  Phase B: lean SST features (enso/pdo/atlantic lags ± iod) per region
  Phase C: lean + belg_antecedent_anom_z for ALL Kiremt regions
  Phase D: region-specific antecedent — lean+ant for 5 regions, lean for 8
             KIREMT_ANTECEDENT_INCLUDE = {amhara, benishangul_gumz, gambela, harari, somali}

Phase history (Belg):
  Phase D: lean baseline (atlantic_lag1/2, enso_lag1, iod_lag1, pdo_lag1)
  Phase E: baseline + amm_sst_jan (uniform, all regions) — rolling-origin Δ +0.030
  Phase F: region-specific AMM — amm_sst_jan for BELG_AMM_INCLUDE, lean for rest
             BELG_AMM_INCLUDE = {addis_ababa, benishangul_gumz, dire_dawa, gambela,
                                  harari, oromia, tigray}
             Phase F aggregate rolling-origin Belg HSS: +0.0707 (ΔF-D = +0.0554)
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import accuracy_score, cohen_kappa_score
import pickle
import os
import sys
import hashlib
import datetime
import sklearn

MODELS_DIR = "models/regions"
os.makedirs(MODELS_DIR, exist_ok=True)

ANTECEDENT_PATH = "data/chirps_belg_historical.csv"
AMM_PATH        = "data/raw/amm_index.csv"

# ── Phase C/D — belg_antecedent_anom_z lookup ────────────────────────────
# Loaded once; {(region, year): z-score} for Kiremt antecedent feature.
_ANTECEDENT_LOOKUP = None

def _load_antecedent():
    global _ANTECEDENT_LOOKUP
    if _ANTECEDENT_LOOKUP is not None:
        return _ANTECEDENT_LOOKUP
    if not os.path.exists(ANTECEDENT_PATH):
        print(f"  WARNING: {ANTECEDENT_PATH} not found. "
              "belg_antecedent_anom_z will be 0.0 for all rows.")
        _ANTECEDENT_LOOKUP = {}
        return _ANTECEDENT_LOOKUP
    df = pd.read_csv(ANTECEDENT_PATH)
    _ANTECEDENT_LOOKUP = {
        (row["region"], int(row["year"])): float(row["belg_antecedent_anom_z"])
        for _, row in df.iterrows()
        if pd.notna(row["belg_antecedent_anom_z"])
    }
    print(f"  Loaded antecedent lookup: {len(_ANTECEDENT_LOOKUP)} (region, year) entries")
    return _ANTECEDENT_LOOKUP


# ── Phase F — amm_sst_jan lookup ─────────────────────────────────────────
# Loaded once; {year: amm_sst_jan_value} for Belg AMM feature.
# amm_sst_jan[Y] = January AMM of forecast year Y (published ~Feb 15, safe ✓).
_AMM_JAN_LOOKUP = None

def _load_amm_jan():
    global _AMM_JAN_LOOKUP
    if _AMM_JAN_LOOKUP is not None:
        return _AMM_JAN_LOOKUP
    if not os.path.exists(AMM_PATH):
        print(f"  WARNING: {AMM_PATH} not found. "
              "amm_sst_jan will be 0.0 (neutral) for all rows.\n"
              "  Run: python scripts/download_amm_index.py")
        _AMM_JAN_LOOKUP = {}
        return _AMM_JAN_LOOKUP
    amm = pd.read_csv(AMM_PATH, parse_dates=["date"])
    _AMM_JAN_LOOKUP = {
        int(row["date"].year): float(row["amm_sst"])
        for _, row in amm.iterrows()
        if row["date"].month == 1 and pd.notna(row["amm_sst"])
    }
    print(f"  Loaded AMM Jan lookup: {len(_AMM_JAN_LOOKUP)} years "
          f"({min(_AMM_JAN_LOOKUP)}–{max(_AMM_JAN_LOOKUP)})")
    return _AMM_JAN_LOOKUP


# ── Phase D — Region-specific antecedent inclusion ───────────────────────
# Changes from Phase C:
#   • belg_antecedent_anom_z retained ONLY for the 5 Kiremt regions where
#     Phase C rolling-origin showed material improvement (Δ > +0.020).
#     Dropped for the 8 regions where ant regressed or was neutral.
#
#     Phase D rolling-origin results (Kiremt aggregate):
#       Phase B (lean-only):    +0.0272
#       Phase C (ant all):      +0.0431   Δ vs B = +0.016
#       Phase D (region-mixed): +0.0634   Δ vs C = +0.020  ← KEPT
#
#   • Per-region antecedent decisions (rolling-origin ΔD-B):
#       lean+ant: amhara (+0.087), benishangul_gumz (+0.100),
#                 gambela (+0.055), harari (+0.078), somali (+0.210)
#       lean-only: addis_ababa, afar, dire_dawa, oromia, sidama,
#                  snnpr, south_west, tigray
#   • Belg models unchanged from Phase B (no clean DJF antecedent baseline).
#
# Phase C notes (unchanged):
#   • belg_antecedent_anom_z = (Belg Mar–May mm − 1991–2020 mean) / std, ±3.
#     NOT gamma-SPI; a standardised anomaly z-score (simpler, consistent).
#
# Phase B notes (unchanged):
#   • *_3mo_mean removed: confirmed mathematically redundant.
#   • enso/iod/pdo/atlantic lag3 removed: weak contributions.
#   • spi_lag3 removed: zeroed to 0.0 at inference (train/inference mismatch fix).
#   • Per-region IOD for Kiremt: iod_lag1 added only where LOOCV HSS improved.

# Phase D: 5 Kiremt regions where belg_antecedent_anom_z is retained.
# Decision: rolling-origin Phase C showed Δ > +0.020 for these regions.
KIREMT_ANTECEDENT_INCLUDE = {"amhara", "benishangul_gumz", "gambela", "harari", "somali"}

KIREMT_BASE_NO_ANT   = ["enso_lag1", "enso_lag2", "pdo_lag1", "pdo_lag2", "atlantic_lag1"]
KIREMT_BASE_WITH_ANT = KIREMT_BASE_NO_ANT + ["belg_antecedent_anom_z"]

# Kiremt regions where adding iod_lag1 raised LOOCV HSS in the v1 per-feature ablation
KIREMT_IOD_INCLUDE = {"amhara", "benishangul_gumz", "somali"}

# Phase F: 7 Belg regions where amm_sst_jan raises rolling-origin HSS vs baseline.
# Decision: Phase E rolling-origin AMM2 > BASELINE for these regions.
# Δ values: addis_ababa (+0.143), benishangul_gumz (+0.006), dire_dawa (+0.117),
#           gambela (+0.214), harari (+0.117), oromia (+0.012), tigray (+0.123).
# Excluded (BASELINE wins): afar (-0.071), amhara (-0.039), sidama (-0.064),
#                            snnpr (-0.020), somali (-0.151), south_west (-0.017).
BELG_AMM_INCLUDE = {
    "addis_ababa", "benishangul_gumz", "dire_dawa", "gambela",
    "harari", "oromia", "tigray",
}

BELG_BASE_FEATURES     = ["atlantic_lag1", "atlantic_lag2", "enso_lag1", "iod_lag1", "pdo_lag1"]
BELG_BASE_WITH_AMM     = BELG_BASE_FEATURES + ["amm_sst_jan"]


def get_feature_cols(region, season):
    """Return the region-specific feature column list for one model.

    Kiremt (Phase D): lean+ant for KIREMT_ANTECEDENT_INCLUDE; lean for others.
    Belg (Phase F): lean+amm_sst_jan for BELG_AMM_INCLUDE; lean for others.
    """
    if season == "Kiremt":
        if region in KIREMT_ANTECEDENT_INCLUDE:
            feats = list(KIREMT_BASE_WITH_ANT)   # 5 SST + antecedent
        else:
            feats = list(KIREMT_BASE_NO_ANT)     # 5 SST only
        if region in KIREMT_IOD_INCLUDE:
            feats.append("iod_lag1")             # +1 for IOD-sensitive regions
        return feats
    else:                                        # Belg — Phase F
        if region in BELG_AMM_INCLUDE:
            return list(BELG_BASE_WITH_AMM)      # 5 baseline + amm_sst_jan
        return list(BELG_BASE_FEATURES)          # 5 baseline only


def _file_sha256(path):
    """Return first 12 chars of SHA-256 hash of a file — for provenance."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


DATA_PATH = "data/processed/seasonal_enriched.parquet"


def load_data():
    df = pd.read_parquet(DATA_PATH)
    print(f"Loaded {len(df)} records, {df['region'].nunique()} regions")
    return df

def build_features(region, region_df, season_key):
    """Build region-specific feature matrix for one region-season slice.

    Uses get_feature_cols(region, season) — a region-specific lean set.
    Injected features (not in seasonal_enriched.parquet):
      belg_antecedent_anom_z — Kiremt Phase D feature (from chirps_belg_historical.csv)
      amm_sst_jan            — Belg Phase F feature   (from data/raw/amm_index.csv)
    Both injected features fall back to 0.0 (climatological neutral) for missing values.
    Core SST-index features: rows with NaN are dropped (no fallback).
    """
    feature_cols = get_feature_cols(region, season_key)
    data = region_df[region_df["season"] == season_key].copy()
    data = data.sort_values("year")

    # Inject antecedent column for Kiremt models (not stored in parquet)
    if "belg_antecedent_anom_z" in feature_cols:
        lookup = _load_antecedent()
        data["belg_antecedent_anom_z"] = data["year"].apply(
            lambda y: lookup.get((region, int(y)), 0.0)
        )

    # Inject AMM Jan column for Belg models (not stored in parquet)
    if "amm_sst_jan" in feature_cols:
        amm_lk = _load_amm_jan()
        data["amm_sst_jan"] = data["year"].apply(
            lambda y: amm_lk.get(int(y), np.nan)
        )

    # Injected feature column names — use 0.0 fallback for missing, not row-drop
    injected = {"belg_antecedent_anom_z", "amm_sst_jan"}

    # Drop rows missing target or any core (non-injected) SST-index feature
    core_cols = [c for c in feature_cols if c not in injected]
    data = data.dropna(subset=["target"] + core_cols)

    available = [c for c in feature_cols if c in data.columns]
    # Fill any remaining NaN in injected features with 0.0
    data[available] = data[available].fillna(0.0)

    X = data[available].values
    y = data["target"].values.astype(int)
    years = data["year"].values
    return X, y, years, available, data  # data returned for per-fold record building

def train_region_model(X, y, years):
    """Train LR model.  Returns (model, metrics, fold_records) or (None, None, [])."""
    if len(np.unique(y)) < 2 or len(X) < 15:
        return None, None, []

    logo = LeaveOneGroupOut()
    y_true_all, y_pred_all = [], []
    fold_records = []   # per-year LOOCV predictions → validation_results.csv

    for train_idx, test_idx in logo.split(X, y, groups=years):
        if len(np.unique(y[train_idx])) < 2:
            continue
        m = LogisticRegression(
            C=0.5, max_iter=1000, class_weight="balanced",
            solver="lbfgs", random_state=42,
        )
        m.fit(X[train_idx], y[train_idx])
        preds = m.predict(X[test_idx])
        probs = m.predict_proba(X[test_idx])   # shape (n_test, 3)
        y_true_all.extend(y[test_idx])
        y_pred_all.extend(preds)
        for i, ti in enumerate(test_idx):
            fold_records.append({
                "year":       int(years[ti]),
                "actual":     int(y[ti]),
                "predicted":  int(preds[i]),
                "correct":    int(y[ti] == preds[i]),
                "prob_below": round(float(probs[i, 0]), 4),
                "prob_near":  round(float(probs[i, 1]), 4),
                "prob_above": round(float(probs[i, 2]), 4),
            })

    if len(y_true_all) < 5:
        return None, None, []

    y_true_all = np.array(y_true_all)
    y_pred_all = np.array(y_pred_all)
    cv_accuracy = accuracy_score(y_true_all, y_pred_all)

    try:
        cv_hss = cohen_kappa_score(y_true_all, y_pred_all)
    except Exception:
        cv_hss = 0.0

    model = LogisticRegression(
        C=0.5, max_iter=1000, class_weight="balanced",
        solver="lbfgs", random_state=42,
    )
    model.fit(X, y)
    train_accuracy = accuracy_score(y, model.predict(X))

    return model, {
        "cv_accuracy":    round(cv_accuracy, 3),
        "cv_hss":         round(cv_hss, 3),
        "train_accuracy": round(train_accuracy, 3),
        "n_samples":      len(X),
    }, fold_records

def train_all_regions():
    print("Loading data...")
    df = load_data()

    regions = sorted(df["region"].unique())
    seasons = ["Kiremt", "Belg"]
    results         = []
    all_fold_records = []   # accumulated LOOCV records → validation_results.csv
    saved   = 0
    skipped = 0

    for region in regions:
        region_df = df[df["region"] == region].copy()
        for season_key in seasons:
            try:
                X, y, years, feature_cols, data = build_features(region, region_df, season_key)
                if len(X) < 15:
                    print(f"  SKIP {region:25s} {season_key} — only {len(X)} samples")
                    skipped += 1
                    continue

                model, metrics, fold_records = train_region_model(X, y, years)
                if model is None:
                    skipped += 1
                    continue

                model_path = os.path.join(MODELS_DIR, f"{region}_{season_key.lower()}.pkl")
                with open(model_path, "wb") as f:
                    pickle.dump({
                        "model":        model,
                        "feature_cols": feature_cols,
                        "region":       region,
                        "season":       season_key,
                        "metrics":      metrics,
                        # ── Provenance ─────────────────────────────────────
                        "trained_at":       datetime.datetime.utcnow().isoformat() + "Z",
                        "sklearn_version":  sklearn.__version__,
                        "data_sha256":      _file_sha256(DATA_PATH),
                        "python_version":   sys.version,
                        "phase":            "F_region_specific_amm",  # Phase F: Kiremt=lean+ant/lean; Belg=lean+amm/lean
                    }, f)

                # Tag fold records with region/season and accumulate
                for rec in fold_records:
                    rec["region"] = region
                    rec["season"] = season_key
                all_fold_records.extend(fold_records)

                results.append({"region": region, "season": season_key, **metrics})
                saved += 1
                print(f"  ✓ {region:25s} {season_key:8s} CV={metrics['cv_accuracy']:.0%} HSS={metrics['cv_hss']:+.3f} n={metrics['n_samples']}")

            except Exception as e:
                print(f"  ERROR {region} {season_key}: {e}")
                skipped += 1

    results_df = pd.DataFrame(results)
    results_df.to_csv("models/regions/training_summary.csv", index=False)

    # ── Save validation_results.csv with reproducible LOOCV predictions ──
    # Columns match data/validation_results.csv schema expected by validation.py
    if all_fold_records:
        val_df = pd.DataFrame(all_fold_records, columns=[
            "region", "season", "year", "actual", "predicted",
            "correct", "prob_below", "prob_near", "prob_above",
        ])
        val_path = "data/validation_results.csv"
        val_df.to_csv(val_path, index=False)
        print(f"\nValidation results saved: {val_path} ({len(val_df)} rows)")

    print(f"\n{'='*60}")
    print(f"Trained: {saved} models")
    print(f"Skipped: {skipped}")
    print(f"\nCV Accuracy:  mean={results_df['cv_accuracy'].mean():.1%}  median={results_df['cv_accuracy'].median():.1%}")
    print(f"HSS:          mean={results_df['cv_hss'].mean():.3f}  models>0: {(results_df['cv_hss'] > 0).sum()}/{len(results_df)}")
    print(f"Best:  {results_df['cv_accuracy'].max():.1%} ({results_df.loc[results_df['cv_accuracy'].idxmax(), 'region']})")
    print(f"Worst: {results_df['cv_accuracy'].min():.1%} ({results_df.loc[results_df['cv_accuracy'].idxmin(), 'region']})")
    print(f"\nModels saved to: models/regions/")
    print(f"IMPORTANT: Re-run app to clear @st.cache_data for loaded models.")
    return results_df

if __name__ == "__main__":
    print("Azmera — Per-Region Model Training")
    print("="*60)
    train_all_regions()
