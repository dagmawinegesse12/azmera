"""
Azmera — 4-Season Model Trainer + LOOCV Validator
Trains one Random Forest per season using leave-one-out cross-validation.

Literature basis:
  - Diro et al. (2008): separate models per Ethiopian rainfall zone
  - NextGen (2021): skill varies by season due to different SST drivers
  - Kiremt driven by ENSO, Belg by Atlantic SST, OND/Bega by IOD

Run from project root:
    python scripts/train_4season_models.py

Outputs:
    models/seasonal/{season}_model.pkl
    data/validation_results_4seasons.csv
"""

import pandas as pd
import numpy as np
import pickle
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FEATURE_COLS = [
    'enso_lag1','iod_lag1','enso_lag2','iod_lag2','enso_lag3','iod_lag3',
    'enso_3mo_mean','iod_3mo_mean','pdo_lag1','pdo_lag2','pdo_lag3',
    'pdo_3mo_mean','atlantic_lag1','atlantic_lag2','atlantic_lag3',
    'atlantic_3mo_mean','spi_lag3',
]

SEASONS = ['Kiremt', 'Belg', 'OND', 'Bega']

DROUGHT_YEARS = [1984, 1994, 2002, 2003, 2009, 2015, 2016, 2022]

def compute_hss(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred, labels=[0,1,2])
    n        = cm.sum()
    correct  = np.diag(cm).sum()
    expected = sum(cm[i,:].sum() * cm[:,i].sum() for i in range(3)) / n
    return (correct - expected) / (n - expected), cm

def train_and_validate():
    df = pd.read_parquet(f'{BASE_DIR}/data/processed/seasonal_4seasons.parquet')
    os.makedirs(f'{BASE_DIR}/models/seasonal', exist_ok=True)

    all_results = []

    print("=" * 60)
    print("LOOCV Validation by Season")
    print("=" * 60)

    for season in SEASONS:
        sdf   = df[df['season'] == season].dropna(subset=FEATURE_COLS)
        years = sorted(sdf['year'].unique())
        results = []

        for year in years:
            train = sdf[sdf['year'] != year]
            test  = sdf[sdf['year'] == year]
            if len(test) == 0:
                continue

            model = RandomForestClassifier(
                n_estimators=200, max_depth=6,
                min_samples_leaf=5, class_weight='balanced',
                random_state=42
            )
            model.fit(train[FEATURE_COLS], train['target'])
            preds = model.predict(test[FEATURE_COLS])
            probs = model.predict_proba(test[FEATURE_COLS])

            for i, (idx, row) in enumerate(test.iterrows()):
                results.append({
                    'year':       int(row['year']),
                    'region':     row['region'],
                    'season':     season,
                    'actual':     int(row['target']),
                    'predicted':  int(preds[i]),
                    'prob_below': float(probs[i][0]),
                    'prob_near':  float(probs[i][1]),
                    'prob_above': float(probs[i][2]),
                    'correct':    int(preds[i]) == int(row['target']),
                })

        results_df = pd.DataFrame(results)
        all_results.append(results_df)

        hss, _ = compute_hss(results_df['actual'], results_df['predicted'])
        acc    = results_df['correct'].mean()

        # Train final model on all data
        final_model = RandomForestClassifier(
            n_estimators=200, max_depth=6,
            min_samples_leaf=5, class_weight='balanced',
            random_state=42
        )
        final_model.fit(sdf[FEATURE_COLS], sdf['target'])

        model_path = f'{BASE_DIR}/models/seasonal/{season.lower()}_model.pkl'
        with open(model_path, 'wb') as f:
            pickle.dump({'model': final_model, 'feature_cols': FEATURE_COLS}, f)

        imp = pd.Series(final_model.feature_importances_, index=FEATURE_COLS)
        top3 = ', '.join(imp.sort_values(ascending=False).head(3).index.tolist())

        print(f"\n{season}")
        print(f"  Accuracy: {acc:.1%}   HSS: {hss:.3f}")
        print(f"  Top predictors: {top3}")
        print(f"  Model saved to {model_path}")

    # Save combined validation results
    combined = pd.concat(all_results)
    out_path = f'{BASE_DIR}/data/validation_results_4seasons.csv'
    combined.to_csv(out_path, index=False)

    print("\n" + "=" * 60)
    print("OVERALL (all 4 seasons)")
    hss_all, _ = compute_hss(combined['actual'], combined['predicted'])
    print(f"  Accuracy: {combined['correct'].mean():.1%}   HSS: {hss_all:.3f}")

    print("\nKey drought year detection:")
    for yr in DROUGHT_YEARS:
        yr_df = combined[(combined['year'] == yr) & (combined['actual'] == 0)]
        if len(yr_df) == 0:
            continue
        hit  = yr_df['correct'].mean()
        prob = yr_df['prob_below'].mean()
        print(f"  {yr}  cases={len(yr_df)}  detected={hit:.1%}  avg_prob={prob:.0%}")

    print(f"\nValidation results saved to {out_path}")
    return combined

if __name__ == '__main__':
    train_and_validate()
