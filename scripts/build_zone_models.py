"""
Azmera — Zone-level Model Training
Trains Logistic Regression (L2, C=0.5) forecast models for all 79 Ethiopian zones.
Run after build_zone_data.py completes.
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

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

MODELS_DIR = "models/zones"
os.makedirs(MODELS_DIR, exist_ok=True)

ZONE_DATA_PATH    = "data/processed/zone_rainfall.parquet"
INDICES_DATA_PATH = "data/processed/seasonal_enriched.parquet"


def _file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


# ── Load zone rainfall data ───────────────────────────────────────
def load_zone_data():
    df = pd.read_parquet(ZONE_DATA_PATH)
    print(f"Loaded {len(df)} records, {df['zone_key'].nunique()} zones")
    return df

# ── Load ocean indices (same as region models) ────────────────────
def load_ocean_indices():
    df = pd.read_parquet("data/processed/seasonal_enriched.parquet")
    # Get ocean index columns — same for all regions, just use one region
    sample = df[df["region"] == "oromia"].copy()
    index_cols = [
        "year", "season",
        "enso_lag1", "enso_lag2", "enso_lag3", "enso_3mo_mean",
        "iod_lag1",  "iod_lag2",  "iod_lag3",  "iod_3mo_mean",
        "pdo_lag1",  "pdo_lag2",  "pdo_lag3",  "pdo_3mo_mean",
        "atlantic_lag1", "atlantic_lag2", "atlantic_lag3", "atlantic_3mo_mean",
    ]
    return sample[index_cols].copy()

# ── Feature engineering ───────────────────────────────────────────
def build_features(zone_df, indices_df, zone_key, season_key):
    """Merge zone rainfall with ocean indices for a given zone/season."""
    zone_season = zone_df[
        (zone_df["zone_key"] == zone_key) &
        (zone_df["season"] == season_key)
    ].copy()

    season_indices = indices_df[indices_df["season"] == season_key].copy()

    merged = zone_season.merge(season_indices, on=["year", "season"], how="inner")
    merged = merged.dropna(subset=["target"])

    feature_cols = [
        "enso_lag1", "enso_lag2", "enso_lag3", "enso_3mo_mean",
        "iod_lag1",  "iod_lag2",  "iod_lag3",  "iod_3mo_mean",
        "pdo_lag1",  "pdo_lag2",  "pdo_lag3",  "pdo_3mo_mean",
        "atlantic_lag1", "atlantic_lag2", "atlantic_lag3", "atlantic_3mo_mean",
        "spi_lag1",
    ]

    # Add SPI lag (previous season SPI as feature)
    merged = merged.sort_values("year")
    merged["spi_lag1"] = merged["spi"].shift(1)
    merged = merged.dropna(subset=["spi_lag1"])

    available = [c for c in feature_cols if c in merged.columns]
    X = merged[available].values
    y = merged["target"].values.astype(int)

    return X, y, merged, available

# ── Train one zone model ──────────────────────────────────────────
def train_zone_model(X, y, merged_years, zone_key, season_key):
    """Train Logistic Regression model for one zone/season."""
    model = LogisticRegression(
        C=0.5,
        max_iter=1000,
        class_weight="balanced",
        solver="lbfgs",
        random_state=42,
    )

    if len(np.unique(y)) < 2 or len(X) < 15:
        return None, None

    # Leave-one-year-out CV — no temporal leakage
    logo = LeaveOneGroupOut()
    years = merged_years  # passed in from caller

    y_true_all, y_pred_all = [], []
    for train_idx, test_idx in logo.split(X, y, groups=years):
        if len(np.unique(y[train_idx])) < 2:
            continue
        m = LogisticRegression(C=0.5, max_iter=1000, class_weight="balanced",
                               solver="lbfgs", random_state=42)
        m.fit(X[train_idx], y[train_idx])
        y_true_all.extend(y[test_idx])
        y_pred_all.extend(m.predict(X[test_idx]))

    if len(y_true_all) < 5:
        return None, None

    y_true_all = np.array(y_true_all)
    y_pred_all = np.array(y_pred_all)
    cv_accuracy = accuracy_score(y_true_all, y_pred_all)

    # HSS (Heidke Skill Score) — same metric as region model
    try:
        cv_hss = cohen_kappa_score(y_true_all, y_pred_all)
    except Exception:
        cv_hss = 0.0

    model.fit(X, y)
    train_accuracy = accuracy_score(y, model.predict(X))

    return model, {
        "cv_accuracy": round(cv_accuracy, 3),
        "cv_hss":      round(cv_hss, 3),
        "train_accuracy": round(train_accuracy, 3),
        "n_samples":   len(X),
    }

# ── Main training loop ────────────────────────────────────────────
def train_all_zones():
    print("Loading data...")
    zone_df   = load_zone_data()
    indices_df = load_ocean_indices()

    zones   = zone_df["zone_key"].unique()
    seasons = ["Kiremt", "Belg"]

    results = []
    saved   = 0
    skipped = 0

    for zone_key in sorted(zones):
        zone_display = zone_df[zone_df["zone_key"] == zone_key]["zone_display"].iloc[0]
        region_key   = zone_df[zone_df["zone_key"] == zone_key]["region_key"].iloc[0]

        for season_key in seasons:
            try:
                X, y, merged, feature_cols = build_features(zone_df, indices_df, zone_key, season_key)

                if len(X) < 15:
                    print(f"  SKIP {zone_display} {season_key} — only {len(X)} samples")
                    skipped += 1
                    continue

                model, metrics = train_zone_model(X, y, merged["year"].values, zone_key, season_key)

                if model is None:
                    skipped += 1
                    continue

                # Save model
                model_path = os.path.join(MODELS_DIR, f"{zone_key}_{season_key.lower()}.pkl")
                with open(model_path, "wb") as f:
                    pickle.dump({
                        "model":        model,
                        "feature_cols": feature_cols,
                        "zone_key":     zone_key,
                        "zone_display": zone_display,
                        "region_key":   region_key,
                        "season":       season_key,
                        "metrics":      metrics,
                        # ── Provenance ─────────────────────────────────────
                        "trained_at":       datetime.datetime.utcnow().isoformat() + "Z",
                        "sklearn_version":  sklearn.__version__,
                        "zone_data_sha256": _file_sha256(ZONE_DATA_PATH),
                        "python_version":   sys.version,
                    }, f)

                results.append({
                    "zone_key":     zone_key,
                    "zone_display": zone_display,
                    "region_key":   region_key,
                    "season":       season_key,
                    **metrics,
                })
                saved += 1
                print(f"  ✓ {zone_display:25s} {season_key:8s} CV={metrics['cv_accuracy']:.0%} n={metrics['n_samples']}")

            except Exception as e:
                print(f"  ERROR {zone_display} {season_key}: {e}")
                skipped += 1

    # Save summary
    results_df = pd.DataFrame(results)
    results_df.to_csv("models/zones/training_summary.csv", index=False)

    print(f"\n{'='*50}")
    print(f"Trained: {saved} models")
    print(f"Skipped: {skipped}")
    print(f"\nAccuracy summary:")
    print(f"  Mean CV accuracy:  {results_df['cv_accuracy'].mean():.1%}")
    print(f"  Median CV accuracy:{results_df['cv_accuracy'].median():.1%}")
    print(f"  Best:  {results_df['cv_accuracy'].max():.1%} ({results_df.loc[results_df['cv_accuracy'].idxmax(), 'zone_display']})")
    print(f"  Worst: {results_df['cv_accuracy'].min():.1%} ({results_df.loc[results_df['cv_accuracy'].idxmin(), 'zone_display']})")
    print(f"\nModels saved to: models/zones/")
    print(f"Next step: update src/forecaster.py to support zone-level forecasting")

    return results_df


if __name__ == "__main__":
    print("Azmera — Zone Model Training")
    print("="*50)
    train_all_zones()
