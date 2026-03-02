"""
Azmera — Ensemble Model Comparison
Tests 4 approaches via LOOCV and compares HSS + drought detection:
  1. Logistic Regression (L2 regularised)
  2. Random Forest (balanced)
  3. Analog Method (nearest historical years by climate state)
  4. Ensemble (weighted average of all three)

Run from project root:
    python scripts/test_ensemble.py

Does NOT modify any existing files.
"""

import pandas as pd
import numpy as np
import pickle
import os
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix
from sklearn.preprocessing import StandardScaler

BASE_DIR = "/Users/negesse/Desktop/Projects/Personal/kiremtai"

FEATURE_COLS = [
    'enso_lag1','iod_lag1','enso_lag2','iod_lag2','enso_lag3','iod_lag3',
    'enso_3mo_mean','iod_3mo_mean','pdo_lag1','pdo_lag2','pdo_lag3',
    'pdo_3mo_mean','atlantic_lag1','atlantic_lag2','atlantic_lag3',
    'atlantic_3mo_mean','spi_lag3','region_encoded','is_kiremt',
]

DROUGHT_YEARS = [1984, 1987, 1991, 1994, 2002, 2003, 2009, 2015, 2016]

# ── Helpers ───────────────────────────────────────────────────────

def compute_hss(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
    n        = cm.sum()
    correct  = np.diag(cm).sum()
    expected = sum(cm[i,:].sum() * cm[:,i].sum() for i in range(3)) / n
    denom    = n - expected
    return (correct - expected) / denom if denom > 0 else 0.0, cm


def analog_predict(train_X, train_y, test_X, k=5):
    """
    For each test row, find k most similar training years by Euclidean
    distance in climate-index space. Return probability distribution
    based on their outcomes.
    """
    # Use only climate index features (not region_encoded / is_kiremt)
    # so analog matching is purely on ocean state
    clim_cols = [c for c in FEATURE_COLS if c not in ('region_encoded', 'is_kiremt', 'spi_lag3')]
    train_X_c = train_X[clim_cols].values
    test_X_c  = test_X[clim_cols].values

    # Normalise within training set
    mu  = train_X_c.mean(axis=0)
    std = train_X_c.std(axis=0) + 1e-8
    train_norm = (train_X_c - mu) / std
    test_norm  = (test_X_c  - mu) / std

    probs_all = []
    preds_all = []

    for test_row in test_norm:
        dists   = np.linalg.norm(train_norm - test_row, axis=1)
        top_k   = np.argsort(dists)[:k]
        outcomes = train_y.values[top_k]

        p = np.array([
            (outcomes == 0).mean(),
            (outcomes == 1).mean(),
            (outcomes == 2).mean(),
        ])
        # Smooth slightly to avoid 0/1 probabilities
        p = (p + 0.05) / (1 + 3 * 0.05)

        probs_all.append(p)
        preds_all.append(np.argmax(p))

    return np.array(preds_all), np.array(probs_all)


def run_loocv_model(df, feature_cols, model_name, model_fn):
    """Run LOOCV for a given model factory function."""
    years   = sorted(df['year'].unique())
    results = []

    for year in years:
        train = df[df['year'] != year].copy()
        test  = df[df['year'] == year].copy()
        if len(test) == 0:
            continue

        X_train = train[feature_cols]
        y_train = train['target']
        X_test  = test[feature_cols]

        if model_name == "Analog":
            preds, probs = analog_predict(X_train, y_train, X_test, k=5)
        else:
            m = model_fn()
            m.fit(X_train, y_train)
            preds = m.predict(X_test)
            probs = m.predict_proba(X_test)

        for i, (idx, row) in enumerate(test.iterrows()):
            results.append({
                'year':       int(year),
                'region':     row['region'],
                'season':     row['season'],
                'actual':     int(row['target']),
                'predicted':  int(preds[i]),
                'prob_below': float(probs[i][0]),
                'prob_near':  float(probs[i][1]),
                'prob_above': float(probs[i][2]),
                'correct':    int(preds[i]) == int(row['target']),
            })

    return pd.DataFrame(results)


def run_ensemble_loocv(df, feature_cols, weights=(0.4, 0.3, 0.3)):
    """
    Run LOOCV ensemble: LR + RF + Analog, weighted average of probabilities.
    weights = (LR_weight, RF_weight, Analog_weight)
    """
    years   = sorted(df['year'].unique())
    results = []
    w_lr, w_rf, w_an = weights

    for year in years:
        train = df[df['year'] != year].copy()
        test  = df[df['year'] == year].copy()
        if len(test) == 0:
            continue

        X_train = train[feature_cols]
        y_train = train['target']
        X_test  = test[feature_cols]

        # LR
        lr = LogisticRegression(
            C=0.1, max_iter=1000, class_weight='balanced',
            solver='lbfgs', random_state=42
        )
        lr.fit(X_train, y_train)
        probs_lr = lr.predict_proba(X_test)

        # RF
        rf = RandomForestClassifier(
            n_estimators=200, max_depth=6, min_samples_leaf=5,
            class_weight='balanced', random_state=42
        )
        rf.fit(X_train, y_train)
        probs_rf = rf.predict_proba(X_test)

        # Analog
        _, probs_an = analog_predict(X_train, y_train, X_test, k=5)

        # Weighted ensemble
        probs_ens = w_lr * probs_lr + w_rf * probs_rf + w_an * probs_an
        preds_ens = np.argmax(probs_ens, axis=1)

        for i, (idx, row) in enumerate(test.iterrows()):
            results.append({
                'year':       int(year),
                'region':     row['region'],
                'season':     row['season'],
                'actual':     int(row['target']),
                'predicted':  int(preds_ens[i]),
                'prob_below': float(probs_ens[i][0]),
                'prob_near':  float(probs_ens[i][1]),
                'prob_above': float(probs_ens[i][2]),
                'correct':    int(preds_ens[i]) == int(row['target']),
            })

    return pd.DataFrame(results)


def print_results(name, rdf):
    """Print full result summary for a model."""
    hss, _ = compute_hss(rdf['actual'], rdf['predicted'])
    acc     = rdf['correct'].mean()

    print(f"\n{'─'*55}")
    print(f"  {name}")
    print(f"{'─'*55}")
    print(f"  Overall accuracy : {acc:.1%}")
    print(f"  HSS              : {hss:.3f}  {'✅ skillful' if hss >= 0.3 else '🟠 marginal' if hss >= 0.1 else '❌ no skill'}")

    print(f"\n  By season:")
    for season, grp in rdf.groupby('season'):
        h, _ = compute_hss(grp['actual'], grp['predicted'])
        print(f"    {season:8s}  acc={grp['correct'].mean():.1%}  HSS={h:.3f}")

    print(f"\n  Key drought years:")
    for yr in DROUGHT_YEARS:
        yr_df = rdf[(rdf['year'] == yr) & (rdf['actual'] == 0)]
        if len(yr_df) == 0:
            continue
        hit  = yr_df['correct'].mean()
        prob = yr_df['prob_below'].mean()
        icon = '✅' if hit >= 0.5 else '🟠' if hit >= 0.3 else '❌'
        print(f"    {icon} {yr}  regions={len(yr_df):2d}  "
              f"detected={hit:.0%}  avg_prob={prob:.0%}")

    return hss, acc


def print_comparison_table(all_results):
    """Print side-by-side comparison of key metrics."""
    print(f"\n{'='*65}")
    print("  SUMMARY COMPARISON")
    print(f"{'='*65}")
    print(f"  {'Model':<30} {'HSS':>8} {'Accuracy':>10} {'2002':>8} {'2009':>8} {'2015':>8}")
    print(f"  {'─'*30} {'─'*8} {'─'*10} {'─'*8} {'─'*8} {'─'*8}")

    for name, rdf in all_results.items():
        hss, _ = compute_hss(rdf['actual'], rdf['predicted'])
        acc     = rdf['correct'].mean()
        row     = [name, f"{hss:.3f}", f"{acc:.1%}"]
        for yr in [2002, 2009, 2015]:
            yr_df = rdf[(rdf['year'] == yr) & (rdf['actual'] == 0)]
            if len(yr_df):
                row.append(f"{yr_df['correct'].mean():.0%}")
            else:
                row.append("n/a")
        print(f"  {row[0]:<30} {row[1]:>8} {row[2]:>10} {row[3]:>8} {row[4]:>8} {row[5]:>8}")

    print(f"{'='*65}")
    print("  WMO skillful threshold: HSS >= 0.300")
    print(f"{'='*65}\n")


# ── Main ──────────────────────────────────────────────────────────

def main():
    print("\n" + "="*65)
    print("  AZMERA — ENSEMBLE MODEL COMPARISON (LOOCV)")
    print("  Testing on seasonal_enriched.parquet")
    print("="*65)

    # Load data
    df = pd.read_parquet(f'{BASE_DIR}/data/processed/seasonal_enriched.parquet')
    with open(f'{BASE_DIR}/models/feature_cols.pkl', 'rb') as f:
        saved_cols = pickle.load(f)

    # Intersect to make sure all cols exist
    feature_cols = [c for c in FEATURE_COLS if c in df.columns]
    print(f"\n  Dataset: {len(df)} rows | {df['year'].nunique()} years | "
          f"{df['region'].nunique()} regions | {df['season'].nunique()} seasons")
    print(f"  Features: {len(feature_cols)} columns\n")

    all_results = {}

    # 1. Logistic Regression
    print("Running Logistic Regression LOOCV...")
    lr_fn = lambda: LogisticRegression(
        C=0.1, max_iter=1000, class_weight='balanced',
        solver='lbfgs', random_state=42
    )
    lr_results = run_loocv_model(df, feature_cols, "LR", lr_fn)
    all_results["Logistic Regression (L2, C=0.1)"] = lr_results
    print_results("Logistic Regression (L2, C=0.1)", lr_results)

    # 2. Random Forest
    print("\nRunning Random Forest LOOCV...")
    rf_fn = lambda: RandomForestClassifier(
        n_estimators=200, max_depth=6, min_samples_leaf=5,
        class_weight='balanced', random_state=42
    )
    rf_results = run_loocv_model(df, feature_cols, "RF", rf_fn)
    all_results["Random Forest (balanced)"] = rf_results
    print_results("Random Forest (balanced)", rf_results)

    # 3. Analog method
    print("\nRunning Analog Method LOOCV (k=5)...")
    analog_results = run_loocv_model(df, feature_cols, "Analog", None)
    all_results["Analog Method (k=5 nearest years)"] = analog_results
    print_results("Analog Method (k=5 nearest years)", analog_results)

    # 4. Ensemble: LR 40% + RF 30% + Analog 30%
    print("\nRunning Ensemble LOOCV (LR=40%, RF=30%, Analog=30%)...")
    ens_results = run_ensemble_loocv(df, feature_cols, weights=(0.4, 0.3, 0.3))
    all_results["Ensemble (LR 40% + RF 30% + Analog 30%)"] = ens_results
    print_results("Ensemble (LR 40% + RF 30% + Analog 30%)", ens_results)

    # 5. Ensemble variant: equal weights
    print("\nRunning Ensemble LOOCV (equal weights 33/33/33)...")
    ens2_results = run_ensemble_loocv(df, feature_cols, weights=(0.33, 0.33, 0.34))
    all_results["Ensemble (equal weights 33/33/33)"] = ens2_results
    print_results("Ensemble (equal weights 33/33/33)", ens2_results)

    # Summary table
    print_comparison_table(all_results)

    # Best model recommendation
    best_name = max(all_results, key=lambda k: compute_hss(
        all_results[k]['actual'], all_results[k]['predicted'])[0])
    best_hss, _ = compute_hss(
        all_results[best_name]['actual'],
        all_results[best_name]['predicted']
    )
    print(f"  → Best model by HSS: {best_name} (HSS={best_hss:.3f})")
    print()


if __name__ == "__main__":
    main()
