"""
Azmera — Forecast Engine
Takes current climate indices → outputs seasonal forecast + advisory
"""

import pandas as pd
import numpy as np
import pickle
import os
import requests

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "../models")
DATA_DIR   = os.path.join(BASE_DIR, "../data/raw")
ZONE_MODELS_DIR = os.path.join(BASE_DIR, "../models/zones")

# Minimum CV accuracy to show a zone forecast (below this = fall back to region)
ZONE_CV_THRESHOLD = 0.0  # Show all zones, confidence indicated in UI

# ── Load region model and encoder ─────────────────────────────────
def load_model():
    with open(os.path.join(MODELS_DIR, "azmera_model_v3.pkl"), "rb") as f:
        model = pickle.load(f)
    with open(os.path.join(MODELS_DIR, "region_encoder.pkl"), "rb") as f:
        le = pickle.load(f)
    with open(os.path.join(MODELS_DIR, "feature_cols.pkl"), "rb") as f:
        feature_cols = pickle.load(f)
    return model, le, feature_cols

# ── Load zone model ───────────────────────────────────────────────
_ZONE_MODEL_CACHE = {}

def load_zone_model(zone_key, season_key):
    """Load a zone-level model. Cached in memory after first load."""
    cache_key = f"{zone_key}_{season_key.lower()}"
    if cache_key in _ZONE_MODEL_CACHE:
        return _ZONE_MODEL_CACHE[cache_key]
    path = os.path.join(ZONE_MODELS_DIR, f"{cache_key}.pkl")
    if not os.path.exists(path):
        _ZONE_MODEL_CACHE[cache_key] = None
        return None
    with open(path, "rb") as f:
        model = pickle.load(f)
    _ZONE_MODEL_CACHE[cache_key] = model
    return model

# ── Load zone centroids ───────────────────────────────────────────
def load_zone_centroids():
    path = os.path.join(BASE_DIR, "../data/zone_centroids.csv")
    return pd.read_csv(path)

# ── Get zones for a region ────────────────────────────────────────
def get_zones_for_region(region_key):
    """Return list of zones for a given region key."""
    # Normalise region key to match centroids file
    centroids = load_zone_centroids()

    # Map app region keys → centroid region keys
    REGION_KEY_MAP = {
        "oromia":             "oromia",
        "amhara":             "amhara",
        "tigray":             "tigray",
        "snnpr":              "southernnationsnationalities",
        "sidama":             "southernnationsnationalities",
        "south_west":         "southernnationsnationalities",
        "afar":               "afar",
        "somali":             "somali",
        "gambela":            "gambelapeoples",
        "benishangul_gumz":   "benshangul_gumaz",
        "addis_ababa":        "addisabeba",
        "dire_dawa":          "diredawa",
        "harari":             "hararipeople",
    }

    centroid_region = REGION_KEY_MAP.get(region_key, region_key)
    zones = centroids[centroids["region_key"] == centroid_region]
    return zones[["zone_key", "zone_display"]].to_dict("records")

# ── Load latest climate indices ───────────────────────────────────
_INDICES_CACHE = None

def get_latest_indices():
    """Load most recent ENSO, IOD, PDO, Atlantic SST values. Cached in memory."""
    global _INDICES_CACHE
    if _INDICES_CACHE is not None:
        return _INDICES_CACHE
    enso = pd.read_csv(os.path.join(DATA_DIR, "enso_index.csv"),
                       parse_dates=["date"]).sort_values("date")
    iod  = pd.read_csv(os.path.join(DATA_DIR, "iod_index.csv"),
                       parse_dates=["date"]).sort_values("date")
    pdo  = pd.read_csv(os.path.join(DATA_DIR, "pdo_index.csv"),
                       parse_dates=["date"]).sort_values("date")
    atl  = pd.read_csv(os.path.join(DATA_DIR, "atlantic_sst.csv"),
                       parse_dates=["date"]).sort_values("date")

    iod  = iod[iod["iod"]  > -999]
    pdo  = pdo[pdo["pdo"]  > -9.0]
    enso = enso[enso["enso"].notna()]
    atl  = atl[atl["atlantic_sst"].notna()]

    def last3(df, col):
        return df[col].dropna().tail(3).values

    _INDICES_CACHE = {
        "enso": last3(enso, "enso"),
        "iod":  last3(iod,  "iod"),
        "pdo":  last3(pdo,  "pdo"),
        "atl":  last3(atl,  "atlantic_sst"),
    }
    return _INDICES_CACHE

def get_food_prices(region):
    """
    Pull latest WFP food prices for a given Ethiopian region from HDX.
    No API key needed — completely free and public.
    """
    import io

    HDX_URL = (
        "https://data.humdata.org/dataset/2e4f1922-e446-4b57-a98a-"
        "d0e2d5e34afa/resource/87bac18e-f3aa-4b29-8cf8-"
        "76763e823dc5/download"
    )

    REGION_MAP = {
        "oromia":           "Oromia",
        "amhara":           "Amhara",
        "tigray":           "Tigray",
        "snnpr":            "SNNPR",
        "afar":             "Afar",
        "somali":           "Somali",
        "gambela":          "Gambela",
        "benishangul_gumz": "B. Gumuz",
        "addis_ababa":      "Addis Ababa",
        "dire_dawa":        "Dire Dawa",
        "harari":           "Harari",
        "sidama":           "SNNPR",
        "south_west":       "SNNPR",
    }

    KEY_CROPS = [
        "Teff", "Teff (white)", "Teff (mixed)",
        "Maize", "Maize (white)",
        "Sorghum", "Sorghum (white)", "Sorghum (mixed)",
        "Wheat", "Wheat (mixed)",
        "Barley",
    ]

    CROP_LABELS = {
        "Teff":            "Teff",
        "Teff (white)":    "Teff (white)",
        "Teff (mixed)":    "Teff",
        "Maize":           "Maize (Bekolo)",
        "Maize (white)":   "Maize (Bekolo)",
        "Sorghum":         "Sorghum (Mashilla)",
        "Sorghum (white)": "Sorghum (Mashilla)",
        "Sorghum (mixed)": "Sorghum (Mashilla)",
        "Wheat":           "Wheat (Sinde)",
        "Wheat (mixed)":   "Wheat (Sinde)",
        "Barley":          "Barley (Gabs)",
    }

    try:
        r = requests.get(HDX_URL, timeout=30)
        r.raise_for_status()

        df = pd.read_csv(io.StringIO(r.text))
        df["date"] = pd.to_datetime(df["date"])

        hdx_region = REGION_MAP.get(region.lower(), "Oromia")
        region_df  = df[
            (df["admin1"] == hdx_region) &
            (df["commodity"].isin(KEY_CROPS))
        ].copy()

        region_df = region_df[region_df["price"] >= 100]

        if region_df.empty:
            region_df = df[
                (df["commodity"].isin(KEY_CROPS)) &
                (df["price"] >= 100)
            ].copy()

        latest_date = region_df["date"].max()
        this_month  = latest_date - pd.DateOffset(months=1)
        last_month  = latest_date - pd.DateOffset(months=2)

        recent = (
            region_df[region_df["date"] >= this_month]
            .groupby("commodity")["price"]
            .mean()
            .reset_index()
            .rename(columns={"price": "price_recent"})
        )

        prev = (
            region_df[
                (region_df["date"] >= last_month) &
                (region_df["date"] <  this_month)
            ]
            .groupby("commodity")["price"]
            .mean()
            .reset_index()
            .rename(columns={"price": "price_prev_month"})
        )

        latest = recent.merge(prev, on="commodity", how="left")
        latest["price_etb"] = latest["price_recent"]
        latest["pct_change"] = (
            (latest["price_recent"] - latest["price_prev_month"])
            / latest["price_prev_month"] * 100
        )
        latest["label"]    = latest["commodity"].map(CROP_LABELS)
        latest["date_str"] = latest_date.strftime("%b %Y")

        results    = []
        seen_labels = set()

        for _, row in latest.iterrows():
            label = row["label"]
            if label in seen_labels or pd.isna(label):
                continue
            seen_labels.add(label)

            pct = row["pct_change"]

            if pd.isna(pct):
                trend     = "⚪"
                trend_str = "No comparison data"
            elif pct > 10:
                trend     = "🔴"
                trend_str = f"+{pct:.0f}% vs last month"
            elif pct > 3:
                trend     = "🟠"
                trend_str = f"+{pct:.0f}% vs last month"
            elif pct < -3:
                trend     = "🟢"
                trend_str = f"{pct:.0f}% vs last month"
            else:
                trend     = "⚪"
                trend_str = f"{pct:+.0f}% vs last month"

            results.append({
                "crop":      label,
                "price_etb": row["price_etb"],
                "unit":      "per quintal (100kg)",
                "date":      row["date_str"],
                "trend":     trend,
                "trend_str": trend_str,
                "region":    hdx_region,
            })

        return results[:5]

    except Exception as e:
        print(f"Food prices error: {e}")
        return []

# ── Build feature vector (region model) ───────────────────────────
def build_features(region, season, indices, le):
    """Build the 19-feature vector for a given region and season."""

    enso3 = indices["enso"]
    iod3  = indices["iod"]
    pdo3  = indices["pdo"]
    atl3  = indices["atl"]

    def safe_get(arr, i):
        try: return float(arr[-(i)])
        except: return 0.0

    features = {
        "enso_lag1":        safe_get(enso3, 1),
        "iod_lag1":         safe_get(iod3,  1),
        "enso_lag2":        safe_get(enso3, 2),
        "iod_lag2":         safe_get(iod3,  2),
        "enso_lag3":        safe_get(enso3, 3),
        "iod_lag3":         safe_get(iod3,  3),
        "enso_3mo_mean":    float(np.mean(enso3)),
        "iod_3mo_mean":     float(np.mean(iod3)),
        "pdo_lag1":         safe_get(pdo3,  1),
        "pdo_lag2":         safe_get(pdo3,  2),
        "pdo_lag3":         safe_get(pdo3,  3),
        "pdo_3mo_mean":     float(np.mean(pdo3)),
        "atlantic_lag1":    safe_get(atl3,  1),
        "atlantic_lag2":    safe_get(atl3,  2),
        "atlantic_lag3":    safe_get(atl3,  3),
        "atlantic_3mo_mean":float(np.mean(atl3)),
        "spi_lag3":         0.0,
        "region_encoded":   int(le.transform([region.lower()])[0]),
        "is_kiremt":        1 if season == "Kiremt" else 0,
    }

    return pd.DataFrame([features])

# ── Build feature vector (zone model) ────────────────────────────
def build_zone_features(indices, spi_lag1=0.0):
    """Build feature vector for zone model (no region encoding needed)."""
    enso3 = indices["enso"]
    iod3  = indices["iod"]
    pdo3  = indices["pdo"]
    atl3  = indices["atl"]

    def safe_get(arr, i):
        try: return float(arr[-(i)])
        except: return 0.0

    return {
        "enso_lag1":         safe_get(enso3, 1),
        "enso_lag2":         safe_get(enso3, 2),
        "enso_lag3":         safe_get(enso3, 3),
        "enso_3mo_mean":     float(np.mean(enso3)),
        "iod_lag1":          safe_get(iod3,  1),
        "iod_lag2":          safe_get(iod3,  2),
        "iod_lag3":          safe_get(iod3,  3),
        "iod_3mo_mean":      float(np.mean(iod3)),
        "pdo_lag1":          safe_get(pdo3,  1),
        "pdo_lag2":          safe_get(pdo3,  2),
        "pdo_lag3":          safe_get(pdo3,  3),
        "pdo_3mo_mean":      float(np.mean(pdo3)),
        "atlantic_lag1":     safe_get(atl3,  1),
        "atlantic_lag2":     safe_get(atl3,  2),
        "atlantic_lag3":     safe_get(atl3,  3),
        "atlantic_3mo_mean": float(np.mean(atl3)),
        "spi_lag1":          spi_lag1,
    }

# ── Main region forecast function ─────────────────────────────────
def forecast(region, season, fast=False):
    """
    Generate seasonal rainfall forecast for a region.

    Args:
        region: Ethiopian region key (e.g. 'oromia')
        season: 'Kiremt' or 'Belg'

    Returns:
        dict with probabilities, prediction, confidence, advisory
    """
    model, le, feature_cols = load_model()
    indices = get_latest_indices()

    X = build_features(region, season, indices, le)
    X = X[feature_cols]

    probs      = model.predict_proba(X)[0]
    pred       = model.predict(X)[0]
    confidence = float(probs.max())

    label_map  = {0: "Below Normal", 1: "Near Normal", 2: "Above Normal"}
    prediction = label_map[pred]

    enso_val = float(indices["enso"][-1])
    enso_str = "El Niño" if enso_val > 0.5 else \
               "La Niña" if enso_val < -0.5 else "Neutral"

    result = {
        "region":      region,
        "season":      season,
        "prediction":  prediction,
        "confidence":  confidence,
        "prob_below":  float(probs[0]),
        "prob_near":   float(probs[1]),
        "prob_above":  float(probs[2]),
        "enso_current": enso_val,
        "enso_phase":  enso_str,
        "source":      "region",
    }
    if not fast:
        result["advisory_en"] = generate_advisory(region, season, prediction,
                                                   confidence, enso_str, probs, "en")
        result["advisory_am"] = generate_advisory(region, season, prediction,
                                                   confidence, enso_str, probs, "am")
    return result

# ── Zone forecast function ────────────────────────────────────────
def forecast_zone(zone_key, zone_display, region_key, season, fast=False):
    """
    Generate zone-level forecast. Falls back to region if CV < threshold.

    Args:
        zone_key:     zone identifier e.g. 'arsi'
        zone_display: display name e.g. 'Arsi'
        region_key:   parent region e.g. 'oromia'
        season:       'Kiremt' or 'Belg'

    Returns:
        dict with forecast + metadata about source and confidence
    """
    indices = get_latest_indices()
    label_map = {0: "Below Normal", 1: "Near Normal", 2: "Above Normal"}

    # Try zone model first
    zone_data = load_zone_model(zone_key, season)

    if zone_data is not None:
        cv_accuracy = zone_data["metrics"]["cv_accuracy"]

        if cv_accuracy >= ZONE_CV_THRESHOLD:
            # Use zone model
            model        = zone_data["model"]
            feature_cols = zone_data["feature_cols"]

            from src.chirps_anomaly import get_zone_spi_lag1
            spi_lag1 = get_zone_spi_lag1(zone_key, season)
            features = build_zone_features(indices, spi_lag1=spi_lag1)
            X = pd.DataFrame([features])[feature_cols]

            probs      = model.predict_proba(X)[0]
            pred       = model.predict(X)[0]
            confidence = float(probs.max())
            prediction = label_map[pred]

            enso_val = float(indices["enso"][-1])
            enso_str = "El Niño" if enso_val > 0.5 else \
                       "La Niña" if enso_val < -0.5 else "Neutral"

            result = {
                "zone":        zone_display,
                "zone_key":    zone_key,
                "region":      region_key,
                "season":      season,
                "prediction":  prediction,
                "confidence":  confidence,
                "prob_below":  float(probs[0]),
                "prob_near":   float(probs[1]),
                "prob_above":  float(probs[2]),
                "enso_current": enso_val,
                "enso_phase":  enso_str,
                "cv_accuracy": cv_accuracy,
                "source":      "zone",
            }
            if not fast:
                result["advisory_en"] = generate_advisory(
                    zone_display, season, prediction,
                    confidence, enso_str, probs, "en")
                result["advisory_am"] = generate_advisory(
                    zone_display, season, prediction,
                    confidence, enso_str, probs, "am")
            return result
        else:
            # Zone model exists but low skill — fall back to region
            result = forecast(region_key, season, fast=fast)
            result["zone"]        = zone_display
            result["zone_key"]    = zone_key
            result["source"]      = "region_fallback"
            result["cv_accuracy"] = cv_accuracy
            result["fallback_reason"] = f"Zone model skill too low ({cv_accuracy:.0%} CV)"
            return result
    else:
        # No zone model — fall back to region
        result = forecast(region_key, season, fast=fast)
        result["zone"]        = zone_display
        result["zone_key"]    = zone_key
        result["source"]      = "region_fallback"
        result["cv_accuracy"] = None
        result["fallback_reason"] = "No zone model available"
        return result

# ── Advisory text generation ──────────────────────────────────────
def generate_advisory(region, season, prediction, confidence,
                      enso_phase, probs, language="en"):
    """Generate farmer advisory using OpenAI."""

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    season_months = "June–September" if season == "Kiremt" \
                    else "March–May"

    prompt = f"""
    You are an expert agricultural advisor specializing in Ethiopian smallholder farming.
    Generate a practical, actionable seasonal forecast advisory with specific crop recommendations.

    Forecast details:
    - Region: {region.title()} 
    - Season: {season} ({season_months})
    - Prediction: {prediction} rainfall
    - Confidence: {confidence:.0%}
    - ENSO Phase: {enso_phase}
    - Drought probability: {probs[0]:.0%}
    - Normal probability:  {probs[1]:.0%}
    - Above normal probability: {probs[2]:.0%}

    Ethiopian crops to consider recommending based on conditions:

    DROUGHT/DRY CONDITIONS — recommend these:
    - Sorghum (Mashilla) — extremely drought tolerant, widely grown in Ethiopia
    - Teff (Eragrostis tef) — Ethiopia's staple grain, moderate drought tolerance
    - Chickpea (Shimbra) — good for drier Belg season, nitrogen fixing
    - Faba Bean (Ater) — tolerates dry spells, important protein source
    - Finger Millet (Dagusa) — very drought hardy, grown in Tigray/SNNPR
    - Groundnut — drought tolerant, good for Afar/Somali lowlands
    - Sesame (Selit) — extremely drought tolerant, cash crop

    NORMAL CONDITIONS — recommend these:
    - Teff — Ethiopia's most important crop, ideal for normal rainfall
    - Maize (Bekolo) — high yield in normal conditions, Oromia/SNNPR staple
    - Wheat (Sinde) — highlands of Amhara/Oromia, needs reliable rain
    - Barley (Gabs) — highland crop, tolerates some variability  
    - Haricot Bean (Adengware) — good companion crop, moderate water needs
    - Sweet Potato — versatile, good food security crop

    ABOVE NORMAL/WET CONDITIONS — recommend these:
    - Maize (Bekolo) — thrives with good rainfall, highest yields
    - Rice — lowland areas like Gambela, needs abundant water
    - Sugarcane — Awash Valley and lowlands
    - Enset (False Banana) — SNNPR staple, loves moisture
    - Coffee (Buna) — highland regions, good with above normal rain
    - Vegetables — tomato, onion, cabbage excellent in wet season

    Write exactly 4 bullet points:
    1. 🌦️ Season outlook in one plain sentence
    2. 🌱 Specific crop recommendations with local names in brackets
    3. 💧 Water/irrigation preparation advice
    4. 🌾 Food storage and risk management advice

    {'Write in Amharic script.' if language == 'am' else 'Write in simple English a farmer can understand.'}

    Keep each bullet to 2 sentences maximum.
    Start each with the emoji shown above.
    Include Ethiopian crop names in brackets where possible.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7
    )

    return response.choices[0].message.content.strip()


# ── Test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Azmera Forecast Engine...\n")

    # Test region forecast
    result = forecast("oromia", "Kiremt")
    print(f"Region:     {result['region'].title()}")
    print(f"Prediction: {result['prediction']} ({result['confidence']:.0%})")

    # Test zone forecast
    print("\nTesting zone forecast — Arsi, Kiremt...")
    zone_result = forecast_zone("arsi", "Arsi", "oromia", "Kiremt")
    print(f"Zone:       {zone_result['zone']}")
    print(f"Prediction: {zone_result['prediction']} ({zone_result['confidence']:.0%})")
    print(f"Source:     {zone_result['source']}")
    if zone_result.get('cv_accuracy'):
        print(f"CV accuracy: {zone_result['cv_accuracy']:.0%}")

    # Test zone list
    print("\nZones in Oromia:")
    for z in get_zones_for_region("oromia"):
        print(f"  {z['zone_display']}")
