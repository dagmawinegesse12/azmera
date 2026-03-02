"""
Azmera — Model Validation Pipeline
Computes leave-one-out cross-validation (LOOCV) and Heidke Skill Score (HSS)
Uses XGBoost matching azmera_model_v3.pkl hyperparameters exactly.
Standard WMO/ICPAC approach for seasonal forecast verification.

Run from project root:
    python scripts/validate_model.py
"""

import pandas as pd
import numpy as np
import pickle
import os
from xgboost import XGBClassifier
from sklearn.metrics import confusion_matrix

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_loocv():
    # ── Load data ─────────────────────────────────────────────────
    df = pd.read_parquet(os.path.join(BASE_DIR, 'data/processed/seasonal_enriched.parquet'))

    with open(os.path.join(BASE_DIR, 'models/feature_cols.pkl'), 'rb') as f:
        feature_cols = pickle.load(f)

    years = sorted(df['year'].unique())
    results = []

    print(f"Running leave-one-out validation across {len(years)} years...")
    print(f"Model: XGBoost (matching azmera_model_v3.pkl hyperparameters)")
    print()

    for year in years:
        train = df[df['year'] != year]
        test  = df[df['year'] == year]

        X_train = train[feature_cols]
        y_train = train['target']
        X_test  = test[feature_cols]

        # Exact hyperparameters from azmera_model_v3.pkl
        model = XGBClassifier(
            n_estimators=500,
            max_depth=5,
            learning_rate=0.03,
            colsample_bytree=0.7,
            gamma=0.1,
            min_child_weight=2,
            eval_metric='mlogloss',
            random_state=42,
            verbosity=0,
        )
        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        probs = model.predict_proba(X_test)

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

    results_df = pd.DataFrame(results)

    # ── Save results ──────────────────────────────────────────────
    out_path = os.path.join(BASE_DIR, 'data/validation_results.csv')
    results_df.to_csv(out_path, index=False)
    print(f"Results saved to {out_path}")
    print()

    # ── Overall accuracy ──────────────────────────────────────────
    accuracy = results_df['correct'].mean()
    print(f"Overall accuracy:          {accuracy:.1%}")

    # ── HSS ───────────────────────────────────────────────────────
    y_true = results_df['actual']
    y_pred = results_df['predicted']
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])

    n        = cm.sum()
    correct  = np.diag(cm).sum()
    expected = sum(cm[i,:].sum() * cm[:,i].sum() for i in range(3)) / n
    hss      = (correct - expected) / (n - expected)

    print(f"Heidke Skill Score (HSS):  {hss:.3f}")
    print(f"  0=no skill | >0.3=good (WMO standard) | 1.0=perfect")
    print()

    # ── By season ─────────────────────────────────────────────────
    print("Accuracy by season:")
    for season, grp in results_df.groupby('season'):
        cm_s = confusion_matrix(grp['actual'], grp['predicted'], labels=[0,1,2])
        n_s  = cm_s.sum()
        c_s  = np.diag(cm_s).sum()
        e_s  = sum(cm_s[i,:].sum() * cm_s[:,i].sum() for i in range(3)) / n_s
        h_s  = (c_s - e_s) / (n_s - e_s)
        print(f"  {season:8s}  accuracy={grp['correct'].mean():.1%}  HSS={h_s:.3f}")
    print()

    # ── By region ─────────────────────────────────────────────────
    print("Accuracy by region:")
    region_stats = []
    for region, grp in results_df.groupby('region'):
        cm_r = confusion_matrix(grp['actual'], grp['predicted'], labels=[0,1,2])
        n_r  = cm_r.sum()
        c_r  = np.diag(cm_r).sum()
        e_r  = sum(cm_r[i,:].sum() * cm_r[:,i].sum() for i in range(3)) / n_r
        h_r  = (c_r - e_r) / (n_r - e_r)
        region_stats.append((region, grp['correct'].mean(), h_r))

    for region, acc, hss_r in sorted(region_stats, key=lambda x: -x[2]):
        print(f"  {region:25s}  accuracy={acc:.1%}  HSS={hss_r:.3f}")
    print()

    # ── Key drought years ─────────────────────────────────────────
    print("Key drought years (Below Normal = 0):")
    drought_years = [1984, 1987, 1991, 1994, 2002, 2003, 2009, 2015, 2016]
    for yr in drought_years:
        yr_df = results_df[(results_df['year'] == yr) & (results_df['actual'] == 0)]
        if len(yr_df) == 0:
            continue
        hit_rate  = yr_df['correct'].mean()
        mean_prob = yr_df['prob_below'].mean()
        print(f"  {yr}  regions={len(yr_df)}  detected={hit_rate:.1%}  avg_prob={mean_prob:.0%}")

    return results_df

if __name__ == "__main__":
    run_loocv()
