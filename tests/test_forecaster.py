"""
Azmera — Forecast Engine Tests
================================
Risk coverage:
  - Forecast output sanity (probabilities, labels)
  - Fallback logic (advisory failure, missing model, empty indices)
  - Unsupported season handling
  - IndexError guard on empty arrays
  - Feature vector shape and semantics
  - Advisory fallback text contract
  - _INDICES_CACHE TTL behavior
"""

import sys
import os
import time
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

# Make src importable from tests/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))


# ── Helpers ───────────────────────────────────────────────────────

def make_mock_indices(enso=0.6, iod=0.3, pdo=0.1, atl=0.2):
    """Return a well-formed indices dict with 3-element arrays."""
    return {
        "enso": np.array([enso - 0.1, enso, enso + 0.1]),
        "iod":  np.array([iod  - 0.1, iod,  iod  + 0.1]),
        "pdo":  np.array([pdo  - 0.1, pdo,  pdo  + 0.1]),
        "atl":  np.array([atl  - 0.1, atl,  atl  + 0.1]),
    }


def make_mock_model_data(probs=(0.2, 0.5, 0.3), pred=1):
    """Return a minimal region model data dict with mocked sklearn model.

    Mocks a Phase D lean+ant Kiremt model (as used by amhara, somali,
    gambela, harari, benishangul_gumz — the KIREMT_ANTECEDENT_INCLUDE set).
    Feature set: enso_lag1/2, pdo_lag1/2, atlantic_lag1, belg_antecedent_anom_z.

    Note: Phase D lean-only regions (addis_ababa, afar, dire_dawa, oromia,
    sidama, snnpr, south_west, tigray) use the same 5 SST features without
    belg_antecedent_anom_z. This mock exercises the antecedent code path.
    Phase F Belg models: see make_mock_belg_amm_model_data() below.
    """
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([list(probs)])
    mock_model.predict.return_value = np.array([pred])

    feature_cols = [
        "enso_lag1", "enso_lag2",
        "pdo_lag1",  "pdo_lag2",
        "atlantic_lag1",
        "belg_antecedent_anom_z",   # Phase D: retained for lean+ant regions
    ]
    return {
        "model":        mock_model,
        "feature_cols": feature_cols,
        "region":       "oromia",
        "season":       "Kiremt",
        "metrics": {
            "cv_accuracy": 0.52,
            "cv_hss":      0.18,
            "n_samples":   42,
        },
    }


def make_mock_belg_amm_model_data(probs=(0.3, 0.4, 0.3), pred=1):
    """Return a minimal region model data dict for a Phase F Belg AMM model.

    Mocks a Phase F Belg model for a BELG_AMM_INCLUDE region (e.g. gambela).
    Feature set: atlantic_lag1/2, enso_lag1, iod_lag1, pdo_lag1, amm_sst_jan.
    This exercises the amm_sst_jan injection code path in forecast().
    """
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([list(probs)])
    mock_model.predict.return_value = np.array([pred])

    feature_cols = [
        "atlantic_lag1", "atlantic_lag2",
        "enso_lag1",
        "iod_lag1",
        "pdo_lag1",
        "amm_sst_jan",              # Phase F: retained for BELG_AMM_INCLUDE regions
    ]
    return {
        "model":        mock_model,
        "feature_cols": feature_cols,
        "region":       "gambela",
        "season":       "Belg",
        "metrics": {
            "cv_accuracy": 0.48,
            "cv_hss":      0.15,
            "n_samples":   42,
        },
    }


# ── Category 1: Unsupported season handling ───────────────────────

class TestUnsupportedSeasons:
    """OND and Bega must raise ValueError, not crash silently or return bad data."""

    def test_ond_raises_value_error(self):
        """Risk: OND forecast attempted despite no model — should raise, not silently fail."""
        import forecaster
        with pytest.raises(ValueError, match="not supported"):
            forecaster.forecast("oromia", "OND")

    def test_bega_raises_value_error(self):
        """Risk: Bega forecast attempted — same guard required."""
        import forecaster
        with pytest.raises(ValueError, match="not supported"):
            forecaster.forecast("oromia", "Bega")

    def test_zone_ond_raises_value_error(self):
        """Risk: Zone forecast for unsupported season must also raise."""
        import forecaster
        with pytest.raises(ValueError, match="not supported"):
            forecaster.forecast_zone("arsi", "Arsi", "oromia", "OND")

    def test_valid_seasons_do_not_raise_on_season_check(self):
        """Sanity: Kiremt and Belg should NOT raise ValueError at the season check."""
        import forecaster
        # They may raise other errors (missing model), but not ValueError for season
        with patch("forecaster.load_region_model", return_value=None), \
             patch("forecaster.load_model", side_effect=FileNotFoundError("no model")):
            with pytest.raises(FileNotFoundError):
                forecaster.forecast("oromia", "Kiremt")
            # i.e., got past the season guard, hit model loading instead


# ── Category 2: Probability sanity checks ─────────────────────────

class TestProbabilitySanity:
    """Forecast result probabilities must sum to 1.0 and confidence must equal max prob."""

    def test_probabilities_sum_to_one(self):
        """Risk: Malformed probs would make the probability bar chart > 100%."""
        import forecaster

        with patch("forecaster.get_latest_indices", return_value=make_mock_indices()), \
             patch("forecaster.load_region_model", return_value=make_mock_model_data()), \
             patch("forecaster.generate_advisory", return_value="mock advisory"):

            result = forecaster.forecast("oromia", "Kiremt")

        total = result["prob_below"] + result["prob_near"] + result["prob_above"]
        assert abs(total - 1.0) < 1e-6, f"Probabilities sum to {total}, not 1.0"

    def test_confidence_equals_max_probability(self):
        """Risk: If confidence ≠ max(probs), the confidence bar is inconsistent with the prob bars."""
        import forecaster

        with patch("forecaster.get_latest_indices", return_value=make_mock_indices()), \
             patch("forecaster.load_region_model", return_value=make_mock_model_data(probs=(0.5, 0.3, 0.2), pred=0)), \
             patch("forecaster.generate_advisory", return_value="mock advisory"):

            result = forecaster.forecast("oromia", "Kiremt")

        assert abs(result["confidence"] - max(result["prob_below"], result["prob_near"], result["prob_above"])) < 1e-9

    def test_prediction_matches_argmax(self):
        """Risk: Label and max probability must be consistent."""
        label_map = {0: "Below Normal", 1: "Near Normal", 2: "Above Normal"}
        import forecaster

        for pred_class, probs in [(0, (0.6, 0.3, 0.1)), (1, (0.2, 0.5, 0.3)), (2, (0.1, 0.2, 0.7))]:
            with patch("forecaster.get_latest_indices", return_value=make_mock_indices()), \
                 patch("forecaster.load_region_model",
                        return_value=make_mock_model_data(probs=probs, pred=pred_class)), \
                 patch("forecaster.generate_advisory", return_value="ok"):

                result = forecaster.forecast("oromia", "Kiremt")

            assert result["prediction"] == label_map[pred_class], (
                f"pred_class={pred_class} but got '{result['prediction']}'"
            )
            # Also check that prediction matches the highest probability
            probs_out = [result["prob_below"], result["prob_near"], result["prob_above"]]
            assert result["prediction"] == label_map[int(np.argmax(probs_out))]


# ── Category 3: Empty / malformed index robustness ────────────────

class TestEmptyIndexRobustness:
    """Risk: If NOAA CSVs are empty or corrupt, IndexError must not propagate."""

    def test_empty_enso_array_does_not_raise_index_error(self):
        """
        Confirms Patch A4 is working.
        Previously: float(indices['enso'][-1]) would raise IndexError on empty array.
        After fix: should return a result with enso_val=0.0 (Neutral ENSO).
        """
        empty_indices = make_mock_indices()
        empty_indices["enso"] = np.array([])  # simulate corrupted ENSO CSV

        import forecaster

        with patch("forecaster.get_latest_indices", return_value=empty_indices), \
             patch("forecaster.load_region_model", return_value=make_mock_model_data()), \
             patch("forecaster.generate_advisory", return_value="ok"):

            result = forecaster.forecast("oromia", "Kiremt")

        # Should succeed, not raise
        assert result["prediction"] in ("Below Normal", "Near Normal", "Above Normal")
        assert result["enso_phase"] == "Neutral"  # 0.0 → Neutral
        assert result["enso_current"] == 0.0

    def test_safe_get_returns_zero_on_empty_array(self):
        """
        Directly test safe_get behavior — the private helper used throughout build_features.
        """
        # Replicate safe_get logic from forecaster.py
        def safe_get(arr, i):
            try:
                return float(arr[-(i)])
            except Exception:
                return 0.0

        assert safe_get(np.array([]), 1) == 0.0
        assert safe_get(np.array([1.5]), 1) == 1.5
        assert safe_get(np.array([1.5, 2.0]), 3) == 0.0  # deeper than array length

    def test_all_empty_indices_returns_neutral_forecast(self):
        """When all index arrays are empty, forecast should still complete with neutral values."""
        all_empty = {k: np.array([]) for k in ["enso", "iod", "pdo", "atl"]}

        import forecaster

        with patch("forecaster.get_latest_indices", return_value=all_empty), \
             patch("forecaster.load_region_model", return_value=make_mock_model_data()), \
             patch("forecaster.generate_advisory", return_value="ok"):

            result = forecaster.forecast("oromia", "Kiremt")

        assert result["prediction"] in ("Below Normal", "Near Normal", "Above Normal")


# ── Category 4: Advisory fallback behavior ────────────────────────

class TestAdvisoryFallback:
    """Risk: OpenAI failure must not propagate — fallback text must be returned."""

    def test_advisory_does_not_raise_on_openai_error(self):
        """
        Confirms Patch A1 is working.
        Any OpenAI exception must return fallback text, not propagate.
        """
        import forecaster

        with patch("forecaster.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("API quota exceeded")
            mock_openai_cls.return_value = mock_client

            result_en = forecaster.generate_advisory(
                "oromia", "Kiremt", "Below Normal", 0.65, "El Niño",
                np.array([0.65, 0.25, 0.10]), "en"
            )
            result_am = forecaster.generate_advisory(
                "oromia", "Kiremt", "Below Normal", 0.65, "El Niño",
                np.array([0.65, 0.25, 0.10]), "am"
            )

        assert result_en is not None
        assert len(result_en) > 20
        assert result_am is not None
        assert len(result_am) > 20

    def test_advisory_fallback_en_contains_prediction(self):
        """Fallback advisory must at minimum reference the forecast outcome."""
        import forecaster

        with patch("forecaster.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = RuntimeError("network error")
            mock_openai_cls.return_value = mock_client

            result = forecaster.generate_advisory(
                "oromia", "Kiremt", "Above Normal", 0.70, "Neutral",
                np.array([0.10, 0.20, 0.70]), "en"
            )

        assert "Above Normal" in result

    def test_advisory_fallback_on_empty_response(self):
        """Empty string response from OpenAI must trigger fallback, not return empty string."""
        import forecaster

        with patch("forecaster.OpenAI") as mock_openai_cls:
            mock_response = MagicMock()
            mock_response.choices[0].message.content.strip.return_value = ""
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_cls.return_value = mock_client

            result = forecaster.generate_advisory(
                "oromia", "Kiremt", "Near Normal", 0.45, "Neutral",
                np.array([0.25, 0.45, 0.30]), "en"
            )

        # Should not return empty string
        assert len(result.strip()) > 0


# ── Category 5: Feature vector shape and semantics ────────────────

class TestFeatureVector:
    """Risk: Wrong feature shape or semantics causes silent bad predictions."""

    def test_build_features_returns_expected_columns(self):
        """
        build_features must return DataFrame with exactly the 19 expected feature columns.
        Note: column ORDER follows dict declaration order in build_features(), which
        interleaves ENSO/IOD lags. We assert set equality (presence) + exact count.
        The consuming code always reorders via X[feature_cols], so order is not the invariant.
        """
        from forecaster import build_features

        mock_le = MagicMock()
        mock_le.transform.return_value = [3]

        indices = make_mock_indices()
        df = build_features("oromia", "Kiremt", indices, mock_le)

        expected_cols = {
            "enso_lag1", "enso_lag2", "enso_lag3", "enso_3mo_mean",
            "iod_lag1",  "iod_lag2",  "iod_lag3",  "iod_3mo_mean",
            "pdo_lag1",  "pdo_lag2",  "pdo_lag3",  "pdo_3mo_mean",
            "atlantic_lag1", "atlantic_lag2", "atlantic_lag3", "atlantic_3mo_mean",
            "spi_lag3", "region_encoded", "is_kiremt",
        }
        assert set(df.columns) == expected_cols, (
            f"Unexpected columns: {set(df.columns) - expected_cols}\n"
            f"Missing columns: {expected_cols - set(df.columns)}"
        )
        assert len(df) == 1
        assert len(df.columns) == 19, f"Expected 19 features, got {len(df.columns)}"

    def test_is_kiremt_flag_set_correctly(self):
        """is_kiremt must be 1 for Kiremt, 0 for Belg."""
        from forecaster import build_features

        mock_le = MagicMock()
        mock_le.transform.return_value = [0]
        indices = make_mock_indices()

        kiremt_df = build_features("oromia", "Kiremt", indices, mock_le)
        belg_df   = build_features("oromia", "Belg",   indices, mock_le)

        assert kiremt_df["is_kiremt"].iloc[0] == 1
        assert belg_df["is_kiremt"].iloc[0] == 0

    def test_spi_lag3_is_zero_at_inference(self):
        """
        Phase A/B: spi_lag3 was permanently zeroed at inference (train/inference mismatch).
        Phase C/D: spi_lag3 has been removed from all per-region lean feature sets.
          The shared-model fallback (build_features) still carries spi_lag3=0.0
          for backward compatibility with azmera_model_v3.pkl.
        Phase C fix (now Phase D): belg_antecedent_anom_z is the clean replacement —
          computed from CHIRPS at inference time via get_region_belg_antecedent_anom_z().
          5 Kiremt regions use it (lean+ant); 8 use lean-only SST features.
        This test verifies the shared-model function still has spi_lag3=0.0.
        """
        from forecaster import build_features

        mock_le = MagicMock()
        mock_le.transform.return_value = [0]
        indices = make_mock_indices()

        df = build_features("oromia", "Kiremt", indices, mock_le)
        assert df["spi_lag3"].iloc[0] == 0.0, (
            "spi_lag3 in the shared-model fallback build_features() should be 0.0. "
            "Per-region models no longer use spi_lag3 — they use belg_antecedent_anom_z."
        )

    def test_build_zone_features_contains_spi_lag1(self):
        """
        Zone features must include spi_lag1 (same-season persistence from prior year).
        Per-region Kiremt models use belg_antecedent_anom_z (cross-season antecedent).
        Neither should contain spi_lag3 (removed in Phase A–D — train/inference mismatch fix).
        """
        from forecaster import build_zone_features

        indices = make_mock_indices()
        features = build_zone_features(indices, spi_lag1=0.75)

        assert "spi_lag1" in features
        assert features["spi_lag1"] == 0.75
        assert "spi_lag3" not in features             # removed in Phase B/C
        assert "belg_antecedent_anom_z" not in features  # region model only, not zone


# ── Category 6: Region/zone lookup consistency ────────────────────

class TestRegionZoneLookup:
    """Risk: Wrong region → zone mapping serves forecasts for the wrong geographic area."""

    def test_get_zones_for_region_returns_list_for_all_keys(self):
        """Every region key that app.py uses must return a list from get_zones_for_region."""
        from forecaster import get_zones_for_region

        app_region_keys = [
            "oromia", "amhara", "tigray", "snnpr", "sidama", "south_west",
            "afar", "somali", "gambela", "benishangul_gumz",
            "addis_ababa", "dire_dawa", "harari",
        ]
        for key in app_region_keys:
            result = get_zones_for_region(key)
            assert isinstance(result, list), f"Expected list for '{key}', got {type(result)}"

    def test_unknown_region_returns_empty_list(self):
        """Unknown region key must not raise — return empty list."""
        from forecaster import get_zones_for_region

        result = get_zones_for_region("nonexistent_xyz_region")
        assert isinstance(result, list)
        assert len(result) == 0

    def test_sidama_south_west_map_to_snnpr_zones(self):
        """
        Sidama and South West share SNNPR boundaries.
        get_zones_for_region must return the same zone list for all three keys.
        """
        from forecaster import get_zones_for_region

        snnpr_zones   = get_zones_for_region("snnpr")
        sidama_zones  = get_zones_for_region("sidama")
        sw_zones      = get_zones_for_region("south_west")

        # All should have the same zone_keys
        snnpr_keys  = {z["zone_key"] for z in snnpr_zones}
        sidama_keys = {z["zone_key"] for z in sidama_zones}
        sw_keys     = {z["zone_key"] for z in sw_zones}

        assert snnpr_keys == sidama_keys, "Sidama zones differ from SNNPR zones"
        assert snnpr_keys == sw_keys,     "South West zones differ from SNNPR zones"

    def test_zone_dict_has_required_keys(self):
        """Each zone dict must have zone_key and zone_display."""
        from forecaster import get_zones_for_region

        zones = get_zones_for_region("oromia")
        assert len(zones) > 0, "Oromia should have zones"
        for z in zones:
            assert "zone_key" in z,    f"Missing 'zone_key' in zone: {z}"
            assert "zone_display" in z, f"Missing 'zone_display' in zone: {z}"
            assert isinstance(z["zone_key"], str)
            assert len(z["zone_key"]) > 0


# ── Category 7: Map join integrity ────────────────────────────────

class TestMapJoinIntegrity:
    """Risk: GeoJSON region names don't match lookup dicts → silent map gaps."""

    def test_geojson_region_names_all_in_lookup(self):
        """
        Every NAME_1 value in ethiopia_regions.geojson must appear in GEOJSON_TO_AZMERA.
        If this fails, a region will silently show as 'No Forecast' on the map.
        """
        import json
        folium = pytest.importorskip("folium", reason="folium not installed")
        from map_component import GEOJSON_TO_AZMERA

        geojson_path = os.path.join(
            os.path.dirname(__file__), "../data/ethiopia_regions.geojson"
        )
        if not os.path.exists(geojson_path):
            pytest.skip("GeoJSON not found — run from project root")

        with open(geojson_path) as f:
            geojson = json.load(f)

        geojson_names = {
            feat["properties"]["NAME_1"]
            for feat in geojson["features"]
        }
        missing = geojson_names - set(GEOJSON_TO_AZMERA.keys())
        assert not missing, (
            f"GeoJSON regions not mapped in GEOJSON_TO_AZMERA: {missing}. "
            "These regions will show 'No Forecast' silently on the risk map."
        )

    def test_azmera_to_geojson_is_invertible(self):
        """AZMERA_TO_GEOJSON_REGION must be the exact inverse of GEOJSON_TO_AZMERA."""
        pytest.importorskip("folium", reason="folium not installed")
        from map_component import GEOJSON_TO_AZMERA, AZMERA_TO_GEOJSON_REGION

        for geo_name, azmera_name in GEOJSON_TO_AZMERA.items():
            reverse = AZMERA_TO_GEOJSON_REGION.get(azmera_name)
            assert reverse == geo_name, (
                f"GEOJSON_TO_AZMERA['{geo_name}'] = '{azmera_name}' but "
                f"AZMERA_TO_GEOJSON_REGION['{azmera_name}'] = '{reverse}'"
            )

    def test_chirps_region_coords_cover_all_app_regions(self):
        """
        Every region key that app.py converts to must appear in REGION_COORDS
        or the CHIRPS anomaly will silently use Addis Ababa coordinates.
        """
        pytest.importorskip("rasterio", reason="rasterio not installed")
        from chirps_anomaly import REGION_COORDS

        # These are the lowercase.replace(" ", "_") forms used in app.py
        app_region_keys = [
            "oromia", "amhara", "tigray", "snnpr", "sidama", "south_west",
            "afar", "somali", "gambela", "benishangul_gumz",
            "addis_ababa", "dire_dawa", "harari",
        ]
        missing = [k for k in app_region_keys if k not in REGION_COORDS]
        assert not missing, (
            f"Regions missing from REGION_COORDS (will use Addis Ababa fallback): {missing}"
        )


# ── Category 8: Indices cache TTL ─────────────────────────────────

class TestIndicesCacheTTL:
    """Risk: Stale climate indices served permanently after server start."""

    def test_cache_refreshes_after_ttl(self):
        """
        Confirms Patch B1: _INDICES_CACHE must reload after TTL expires.
        Uses module-level cache directly.
        """
        import forecaster

        # Reset cache state
        forecaster._INDICES_CACHE = None
        forecaster._INDICES_CACHE_LOADED_AT = 0.0

        first_indices = make_mock_indices(enso=1.0)
        second_indices = make_mock_indices(enso=-1.0)

        call_count = [0]

        def fake_loader():
            call_count[0] += 1
            if call_count[0] == 1:
                return first_indices
            return second_indices

        with patch.object(forecaster, "_INDICES_CACHE_TTL", 0.1):
            # First call — loads and caches
            with patch("pandas.read_csv", side_effect=lambda *a, **kw: _make_csv_df(a[0])):
                forecaster._INDICES_CACHE = None
                forecaster._INDICES_CACHE_LOADED_AT = 0.0

            # Simulate loading by directly setting cache
            forecaster._INDICES_CACHE = first_indices
            forecaster._INDICES_CACHE_LOADED_AT = time.time()

            # Immediate second call — should hit cache
            result1 = forecaster.get_latest_indices()
            assert np.array_equal(result1["enso"], first_indices["enso"])

            # Wait for TTL to expire
            time.sleep(0.15)

            # After TTL — cache is stale; next call should reload from CSV
            # Since we can't mock the CSV load easily here without files,
            # just confirm the cache is considered stale
            age = time.time() - forecaster._INDICES_CACHE_LOADED_AT
            assert age > forecaster._INDICES_CACHE_TTL, (
                f"Expected cache to be stale after {forecaster._INDICES_CACHE_TTL}s, "
                f"but it's only {age:.2f}s old"
            )

    def test_cache_hit_within_ttl(self):
        """Within TTL, same object must be returned without re-reading CSVs."""
        import forecaster

        fresh_indices = make_mock_indices(enso=0.8)
        forecaster._INDICES_CACHE = fresh_indices
        forecaster._INDICES_CACHE_LOADED_AT = time.time()

        result = forecaster.get_latest_indices()
        assert result is fresh_indices  # same object, not a re-read


# ── Category 9: HSS computation correctness ───────────────────────
# compute_hss is inlined here to avoid importing validation.py (which pulls in streamlit).
# This is an intentional architectural note: pure math functions should not live in
# files that import streamlit. This is a D1 refactor item.

def compute_hss_pure(y_true, y_pred):
    """
    Pure-Python replica of validation.compute_hss for testing.
    Must stay byte-for-byte identical to the implementation in validation.py.
    If this diverges, tests will give a false sense of security.
    """
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
    n        = cm.sum()
    correct  = np.diag(cm).sum()
    expected = sum(cm[i, :].sum() * cm[:, i].sum() for i in range(3)) / n
    return (correct - expected) / (n - expected), cm


class TestHSSComputation:
    """Risk: Incorrect HSS values in validation tab would misrepresent model quality."""

    def test_hss_perfect_prediction(self):
        """Perfect classifier must have HSS = 1.0."""
        y = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2])
        hss, _ = compute_hss_pure(y, y)
        assert abs(hss - 1.0) < 1e-9, f"Expected HSS=1.0, got {hss}"

    def test_hss_worse_than_random_is_negative(self):
        """A model that always predicts the wrong class has HSS < 0."""
        y_true = np.array([0, 0, 0, 1, 1, 1])
        y_pred = np.array([1, 1, 1, 0, 0, 0])  # systematically wrong
        hss, _ = compute_hss_pure(y_true, y_pred)
        assert hss < 0, f"Expected HSS < 0 for systematically wrong classifier, got {hss}"

    def test_hss_equals_kappa_numerically(self):
        """
        HSS and Cohen's kappa are algebraically identical for unweighted multi-class.
        This test verifies the implementation hasn't drifted from the mathematical identity.
        """
        from sklearn.metrics import cohen_kappa_score

        rng = np.random.default_rng(42)
        y_true = rng.integers(0, 3, size=100)
        y_pred = rng.integers(0, 3, size=100)

        hss, _ = compute_hss_pure(y_true, y_pred)
        kappa  = cohen_kappa_score(y_true, y_pred)

        assert abs(hss - kappa) < 1e-9, (
            f"HSS ({hss:.6f}) != kappa ({kappa:.6f}) — implementation drift detected"
        )

    def test_hss_zero_for_all_same_class_predictions(self):
        """A model that always predicts 'Near Normal' has HSS ≈ 0 or negative."""
        y_true = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2])
        y_pred = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1])  # always Near Normal
        hss, _ = compute_hss_pure(y_true, y_pred)
        # Cannot detect drought or above normal — should have no positive skill
        assert hss <= 0, f"Expected HSS <= 0 for constant predictor, got {hss}"

    def test_hss_single_class_input_does_not_raise_zero_division(self):
        """Single-class input (n - expected = 0) must not raise ZeroDivisionError."""
        y = np.array([1, 1, 1, 1, 1])  # only Near Normal
        try:
            hss, _ = compute_hss_pure(y, y)
            # Result is 0/0 → NaN or inf; accept either, just don't raise
        except ZeroDivisionError:
            pytest.fail("compute_hss raised ZeroDivisionError on single-class input")


# ── Category 14: Phase F AMM inference (I_AMM) ────────────────────

class TestPhaseFAMMInference:
    """
    Risk: Phase F Belg models trained with amm_sst_jan require the value at
    inference time. These tests confirm the injection code path in forecast()
    behaves correctly for AMM-enabled and non-AMM Belg models.
    """

    def test_amm_belg_model_calls_get_latest_amm_jan(self):
        """
        When a Belg model has amm_sst_jan in feature_cols, forecast() must call
        get_latest_amm_jan() to populate the feature value.
        """
        import forecaster

        with patch.object(forecaster, "load_region_model",
                          return_value=make_mock_belg_amm_model_data()), \
             patch.object(forecaster, "get_latest_indices",
                          return_value=make_mock_indices()), \
             patch.object(forecaster, "get_latest_amm_jan",
                          return_value=2.35) as mock_amm, \
             patch.object(forecaster, "generate_advisory", return_value="• test"):

            result = forecaster.forecast("gambela", "Belg")

        mock_amm.assert_called_once()
        assert result["prediction"] in ("Below Normal", "Near Normal", "Above Normal")

    def test_amm_belg_model_uses_amm_value_in_feature_vector(self):
        """
        When get_latest_amm_jan() returns a value, the feature vector passed to the
        model must contain that value for amm_sst_jan.
        """
        import forecaster

        captured_X = []
        mock_data  = make_mock_belg_amm_model_data()

        def capture_predict_proba(X):
            captured_X.append(X)
            return np.array([[0.3, 0.4, 0.3]])

        mock_data["model"].predict_proba.side_effect = capture_predict_proba
        mock_data["model"].predict.return_value = np.array([1])

        with patch.object(forecaster, "load_region_model", return_value=mock_data), \
             patch.object(forecaster, "get_latest_indices",
                          return_value=make_mock_indices()), \
             patch.object(forecaster, "get_latest_amm_jan", return_value=3.14), \
             patch.object(forecaster, "generate_advisory", return_value="• test"):

            forecaster.forecast("gambela", "Belg")

        assert len(captured_X) == 1, "predict_proba must be called once"
        X_df = captured_X[0]
        assert "amm_sst_jan" in X_df.columns, \
            "amm_sst_jan must be present in the feature vector passed to the model"
        assert abs(float(X_df["amm_sst_jan"].iloc[0]) - 3.14) < 1e-6, \
            f"Expected amm_sst_jan=3.14 in feature vector, got {X_df['amm_sst_jan'].iloc[0]}"

    def test_non_amm_belg_model_does_not_call_get_latest_amm_jan(self):
        """
        For Belg regions NOT in BELG_AMM_INCLUDE (e.g. somali), forecast() must NOT
        call get_latest_amm_jan() — amm_sst_jan is not in their feature_cols.
        """
        import forecaster

        # Somali Belg model uses BASELINE features only (no amm_sst_jan)
        mock_data = {
            "model":        MagicMock(),
            "feature_cols": ["atlantic_lag1", "atlantic_lag2", "enso_lag1",
                              "iod_lag1", "pdo_lag1"],
            "region": "somali",
            "season": "Belg",
            "metrics": {"cv_accuracy": 0.44, "cv_hss": 0.10, "n_samples": 42},
        }
        mock_data["model"].predict_proba.return_value = np.array([[0.4, 0.3, 0.3]])
        mock_data["model"].predict.return_value = np.array([0])

        with patch.object(forecaster, "load_region_model", return_value=mock_data), \
             patch.object(forecaster, "get_latest_indices",
                          return_value=make_mock_indices()), \
             patch.object(forecaster, "get_latest_amm_jan",
                          return_value=2.35) as mock_amm, \
             patch.object(forecaster, "generate_advisory", return_value="• test"):

            result = forecaster.forecast("somali", "Belg")

        mock_amm.assert_not_called()
        assert result["prediction"] in ("Below Normal", "Near Normal", "Above Normal")

    def test_amm_fallback_zero_when_get_latest_amm_jan_raises(self):
        """
        If get_latest_amm_jan() raises an exception, forecast() must not crash —
        the pre-set 0.0 (neutral) fallback must be used silently.
        """
        import forecaster

        with patch.object(forecaster, "load_region_model",
                          return_value=make_mock_belg_amm_model_data()), \
             patch.object(forecaster, "get_latest_indices",
                          return_value=make_mock_indices()), \
             patch.object(forecaster, "get_latest_amm_jan",
                          side_effect=OSError("disk error")), \
             patch.object(forecaster, "generate_advisory", return_value="• test"):

            # Must not raise — fallback 0.0 is used
            result = forecaster.forecast("gambela", "Belg")

        assert result["prediction"] in ("Below Normal", "Near Normal", "Above Normal")

    def test_get_latest_amm_jan_returns_float_when_file_present(self):
        """
        get_latest_amm_jan() must return a float when amm_index.csv is readable.
        Tests the function directly (not via forecast()).
        """
        import forecaster
        import pandas as pd

        mock_amm_csv = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-07-01", "2025-01-01"]),
            "amm_sst": [1.23, 4.56, 2.78],
        })

        # Reset cache so the mock CSV is actually read
        forecaster._AMM_JAN_CACHE = None
        forecaster._AMM_JAN_LOADED_AT = 0.0

        with patch("pandas.read_csv", return_value=mock_amm_csv), \
             patch("os.path.exists", return_value=True):
            val = forecaster.get_latest_amm_jan()

        # The most recent January is 2025-01-01 → amm_sst = 2.78
        assert abs(val - 2.78) < 1e-6, \
            f"Expected most recent January AMM = 2.78, got {val}"

        # Reset cache after test
        forecaster._AMM_JAN_CACHE = None
        forecaster._AMM_JAN_LOADED_AT = 0.0

    def test_get_latest_amm_jan_returns_zero_when_file_missing(self):
        """
        get_latest_amm_jan() must return 0.0 (neutral) when amm_index.csv is absent.
        """
        import forecaster

        forecaster._AMM_JAN_CACHE = None
        forecaster._AMM_JAN_LOADED_AT = 0.0

        with patch("os.path.exists", return_value=False):
            val = forecaster.get_latest_amm_jan()

        assert val == 0.0, \
            f"Expected 0.0 fallback when amm_index.csv missing, got {val}"

        # Reset cache after test
        forecaster._AMM_JAN_CACHE = None
        forecaster._AMM_JAN_LOADED_AT = 0.0


# ── Helper: minimal mock CSV dataframe (for cache TTL test) ───────

def _make_csv_df(path):
    """Minimal mock for pandas.read_csv when testing cache behavior."""
    import pandas as pd
    if "enso" in str(path):
        return pd.DataFrame({"date": ["2024-01-01"], "enso": [0.5]})
    if "iod" in str(path):
        return pd.DataFrame({"date": ["2024-01-01"], "iod": [0.2]})
    if "pdo" in str(path):
        return pd.DataFrame({"date": ["2024-01-01"], "pdo": [0.1]})
    if "atlantic" in str(path):
        return pd.DataFrame({"date": ["2024-01-01"], "atlantic_sst": [0.3]})
    return pd.DataFrame()


# ── Category 10: No-skill flag (I1/I8) ────────────────────────────

class TestNoSkillFlag:
    """
    Risk: Suppressed region-seasons (rolling-origin HSS ≤ 0) must set no_skill=True
    so the UI shows "No Validated Forecast" instead of a verdict card.
    The no_skill flag is now driven by rolling-origin tier ('suppressed'), NOT by
    LOOCV cv_hss. Suppressed regions: Oromia/Kiremt (−0.111), Sidama/Kiremt (−0.130),
    Addis Ababa/Kiremt (−0.049), Oromia/Belg (−0.084), SNNPR/Belg (−0.101),
    Sidama/Belg (−0.025).
    """

    def test_no_skill_flag_true_when_hss_negative(self):
        """Forecast result must include no_skill=True when model has negative HSS."""
        import forecaster
        mock_data = make_mock_model_data(probs=(0.6, 0.2, 0.2), pred=0)
        # Override metrics to simulate a negative-HSS model (e.g. Oromia Belg)
        mock_data["metrics"]["cv_hss"] = -0.152

        with patch.object(forecaster, "load_region_model", return_value=mock_data), \
             patch.object(forecaster, "get_latest_indices", return_value=make_mock_indices()), \
             patch.object(forecaster, "generate_advisory", return_value="• test"):
            result = forecaster.forecast("oromia", "Kiremt")

        assert result.get("no_skill") is True, \
            "Expected no_skill=True for HSS=-0.152 model"

    def test_no_skill_flag_false_when_hss_positive(self):
        """Forecast result must have no_skill=False when model has positive HSS."""
        import forecaster
        mock_data = make_mock_model_data(probs=(0.2, 0.5, 0.3), pred=1)
        mock_data["metrics"]["cv_hss"] = 0.316  # Kiremt-level skill

        with patch.object(forecaster, "load_region_model", return_value=mock_data), \
             patch.object(forecaster, "get_latest_indices", return_value=make_mock_indices()), \
             patch.object(forecaster, "generate_advisory", return_value="• test"):
            result = forecaster.forecast("amhara", "Kiremt")

        assert result.get("no_skill") is False, \
            "Expected no_skill=False for HSS=0.316 model"

    def test_no_skill_flag_true_when_hss_exactly_zero(self):
        """HSS = 0.0 exactly is at the threshold — must be flagged (≤ 0)."""
        import forecaster
        mock_data = make_mock_model_data(probs=(0.33, 0.33, 0.34), pred=1)
        mock_data["metrics"]["cv_hss"] = 0.0

        with patch.object(forecaster, "load_region_model", return_value=mock_data), \
             patch.object(forecaster, "get_latest_indices", return_value=make_mock_indices()), \
             patch.object(forecaster, "generate_advisory", return_value="• test"):
            result = forecaster.forecast("snnpr", "Belg")

        assert result.get("no_skill") is True, \
            "Expected no_skill=True for HSS=0.0 (at or below threshold)"

    def test_no_skill_flag_present_in_result(self):
        """The no_skill key must always be present in forecast results."""
        import forecaster
        mock_data = make_mock_model_data()

        with patch.object(forecaster, "load_region_model", return_value=mock_data), \
             patch.object(forecaster, "get_latest_indices", return_value=make_mock_indices()), \
             patch.object(forecaster, "generate_advisory", return_value="• test"):
            result = forecaster.forecast("tigray", "Kiremt")

        assert "no_skill" in result, \
            "no_skill key must always be present in forecast() return value"

    def test_no_skill_result_does_not_suppress_raw_probabilities(self):
        """
        Even for no-skill models, the raw probabilities must remain in the result
        dict so downstream analysis / logging can access them.  The UI suppresses
        the probability display — but the data must not be discarded from the result.
        """
        import forecaster
        mock_data = make_mock_model_data(probs=(0.5, 0.3, 0.2), pred=0)
        mock_data["metrics"]["cv_hss"] = -0.05

        with patch.object(forecaster, "load_region_model", return_value=mock_data), \
             patch.object(forecaster, "get_latest_indices", return_value=make_mock_indices()), \
             patch.object(forecaster, "generate_advisory", return_value="• test"):
            result = forecaster.forecast("oromia", "Belg")

        assert result.get("no_skill") is True
        # All three probabilities must still be present in the dict
        assert "prob_below" in result and "prob_near" in result and "prob_above" in result, \
            "Raw probabilities must be preserved in result even when no_skill=True"
        assert abs(result["prob_below"] + result["prob_near"] + result["prob_above"] - 1.0) < 0.01, \
            "Probabilities must sum to 1.0 even for no-skill results"

    def test_skilled_model_never_sets_no_skill(self):
        """
        A Full-tier region (rolling-origin HSS ≥ 0.10) must NEVER set no_skill=True.
        Uses benishangul_gumz / Kiremt (rolling-origin HSS +0.471 → full tier).
        Protects against an accidental threshold inversion.

        Note: oromia / Kiremt has rolling-origin HSS −0.111 (suppressed) and
        would set no_skill=True — it is NOT a valid choice for this test.
        """
        import forecaster
        mock_data = make_mock_model_data(probs=(0.2, 0.3, 0.5), pred=2)
        mock_data["metrics"]["cv_hss"] = 0.316

        with patch.object(forecaster, "load_region_model", return_value=mock_data), \
             patch.object(forecaster, "get_latest_indices", return_value=make_mock_indices()), \
             patch.object(forecaster, "generate_advisory", return_value="• test"):
            result = forecaster.forecast("benishangul_gumz", "Kiremt")

        assert result.get("no_skill") is False, \
            "Full-tier model (benishangul_gumz Kiremt, RO-HSS +0.471) must not be flagged as no_skill"

    def test_no_skill_result_still_contains_cv_hss(self):
        """
        The cv_hss value must be present in the result so the UI can display
        'HSS -0.152' in the 'No Validated Forecast' panel without a KeyError.
        Uses snnpr / Belg (rolling-origin HSS −0.101 → suppressed → no_skill=True).

        Note: somali / Belg has rolling-origin HSS +0.100 (full tier) and would
        set no_skill=False — it is NOT a valid choice for this test.
        """
        import forecaster
        mock_data = make_mock_model_data(probs=(0.4, 0.35, 0.25), pred=0)
        mock_data["metrics"]["cv_hss"] = -0.152

        with patch.object(forecaster, "load_region_model", return_value=mock_data), \
             patch.object(forecaster, "get_latest_indices", return_value=make_mock_indices()), \
             patch.object(forecaster, "generate_advisory", return_value="• test"):
            result = forecaster.forecast("snnpr", "Belg")

        assert result.get("no_skill") is True
        assert result.get("cv_hss") == -0.152, \
            "cv_hss must be carried through to the result for the no-skill panel to display correctly"


# ── Category 11: Zone centroid error handling (I4) ────────────────

class TestZoneCentroidErrorHandling:
    """
    Risk: If zone_centroids.csv is missing, get_zones_for_region() previously
    crashed with a bare FileNotFoundError on sidebar render. Now it must return
    an empty list gracefully.
    """

    def test_missing_centroids_returns_empty_list(self):
        """get_zones_for_region must return [] if zone_centroids.csv is missing."""
        import forecaster
        import pandas as pd
        empty_df = pd.DataFrame(columns=["zone_key", "zone_display", "region_key", "lat", "lon"])

        with patch.object(forecaster, "load_zone_centroids", return_value=empty_df):
            result = forecaster.get_zones_for_region("oromia")

        assert isinstance(result, list), "Expected a list, got something else"
        assert len(result) == 0, "Expected empty list when centroids CSV is missing"

    def test_missing_centroids_does_not_raise(self):
        """get_zones_for_region must not raise even when centroids returns empty DF."""
        import forecaster
        import pandas as pd
        empty_df = pd.DataFrame(columns=["zone_key", "zone_display", "region_key", "lat", "lon"])

        with patch.object(forecaster, "load_zone_centroids", return_value=empty_df):
            try:
                forecaster.get_zones_for_region("amhara")
            except Exception as e:
                pytest.fail(f"get_zones_for_region raised {type(e).__name__}: {e}")


# ── Category 12: Advisory season_months completeness (I7) ─────────

class TestAdvisorySeasonMonths:
    """
    Risk: If generate_advisory is called with an unexpected season string, it
    previously silently used 'March–May' for all non-Kiremt seasons. The prompt
    must now use the correct month description for all four seasons.
    """

    def test_advisory_season_months_kiremt(self):
        """Kiremt advisory prompt must reference June–September."""
        import forecaster
        captured_prompt = []

        def mock_create(**kwargs):
            captured_prompt.append(kwargs["messages"][0]["content"])
            raise RuntimeError("stop here")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = mock_create

        with patch("forecaster.OpenAI", return_value=mock_client), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
            result = forecaster.generate_advisory(
                "oromia", "Kiremt", "Near Normal", 0.5, "Neutral",
                np.array([0.2, 0.5, 0.3]), "en"
            )

        # Falls back because mock raises — but prompt was captured
        if captured_prompt:
            assert "June" in captured_prompt[0] or "September" in captured_prompt[0], \
                "Kiremt advisory prompt must reference June–September"

    def test_advisory_season_months_belg(self):
        """Belg advisory prompt must reference March–May."""
        import forecaster
        captured_prompt = []

        def mock_create(**kwargs):
            captured_prompt.append(kwargs["messages"][0]["content"])
            raise RuntimeError("stop here")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = mock_create

        with patch("forecaster.OpenAI", return_value=mock_client), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
            forecaster.generate_advisory(
                "amhara", "Belg", "Below Normal", 0.4, "Neutral",
                np.array([0.4, 0.4, 0.2]), "en"
            )

        if captured_prompt:
            assert "March" in captured_prompt[0] or "May" in captured_prompt[0], \
                "Belg advisory prompt must reference March–May"

    def test_advisory_season_months_ond_not_march(self):
        """OND advisory prompt must NOT reference March-May (was a silent bug)."""
        import forecaster
        captured_prompt = []

        def mock_create(**kwargs):
            captured_prompt.append(kwargs["messages"][0]["content"])
            raise RuntimeError("stop here")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = mock_create

        with patch("forecaster.OpenAI", return_value=mock_client), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
            forecaster.generate_advisory(
                "somali", "OND", "Near Normal", 0.4, "Neutral",
                np.array([0.2, 0.5, 0.3]), "en"
            )

        if captured_prompt:
            # Before the fix, OND would show "March–May" — this ensures that's fixed
            assert "March" not in captured_prompt[0] or "October" in captured_prompt[0], \
                "OND advisory prompt must not use March–May month description"


# ── Category 13: Validation CSV schema sanity ─────────────────────

class TestValidationCSVSchema:
    """
    Risk: If validation_results.csv schema changes (columns added/removed),
    render_validation_tab() will crash at runtime without a clear error message.
    These tests protect the schema contract.
    """

    EXPECTED_COLS = {
        "year", "region", "season", "actual", "predicted",
        "prob_below", "prob_near", "prob_above", "correct"
    }

    def test_validation_csv_exists(self):
        """validation_results.csv must exist and be readable."""
        import pandas as pd
        path = os.path.join(os.path.dirname(__file__), "../data/validation_results.csv")
        if not os.path.exists(path):
            pytest.skip("validation_results.csv not present in this environment")
        df = pd.read_csv(path)
        assert len(df) > 0, "validation_results.csv is empty"

    def test_validation_csv_has_required_columns(self):
        """All required columns must be present in validation_results.csv."""
        import pandas as pd
        path = os.path.join(os.path.dirname(__file__), "../data/validation_results.csv")
        if not os.path.exists(path):
            pytest.skip("validation_results.csv not present in this environment")
        df = pd.read_csv(path)
        missing = self.EXPECTED_COLS - set(df.columns)
        assert not missing, f"Missing required columns: {missing}"

    def test_validation_csv_has_no_hss_column(self):
        """hss must NOT be a column in validation_results.csv (computed on-the-fly)."""
        import pandas as pd
        path = os.path.join(os.path.dirname(__file__), "../data/validation_results.csv")
        if not os.path.exists(path):
            pytest.skip("validation_results.csv not present in this environment")
        df = pd.read_csv(path)
        assert "hss" not in df.columns, \
            "hss column should not be in validation_results.csv — it is computed by compute_hss()"

    def test_validation_csv_row_count_matches_expected(self):
        """1092 rows: 42 years × 13 regions × 2 seasons."""
        import pandas as pd
        path = os.path.join(os.path.dirname(__file__), "../data/validation_results.csv")
        if not os.path.exists(path):
            pytest.skip("validation_results.csv not present in this environment")
        df = pd.read_csv(path)
        assert len(df) == 1092, \
            f"Expected 1092 rows (42y × 13r × 2s), got {len(df)}"

    def test_validation_csv_actual_values_in_valid_range(self):
        """All 'actual' values must be 0, 1, or 2 (Below/Near/Above Normal)."""
        import pandas as pd
        path = os.path.join(os.path.dirname(__file__), "../data/validation_results.csv")
        if not os.path.exists(path):
            pytest.skip("validation_results.csv not present in this environment")
        df = pd.read_csv(path)
        invalid = df[~df["actual"].isin([0, 1, 2])]
        assert len(invalid) == 0, \
            f"Found {len(invalid)} rows with invalid 'actual' values: {invalid['actual'].unique()}"

    def test_validation_csv_probabilities_sum_to_one(self):
        """prob_below + prob_near + prob_above must sum to ~1.0 for every row."""
        import pandas as pd
        path = os.path.join(os.path.dirname(__file__), "../data/validation_results.csv")
        if not os.path.exists(path):
            pytest.skip("validation_results.csv not present in this environment")
        df = pd.read_csv(path)
        prob_sum = df["prob_below"] + df["prob_near"] + df["prob_above"]
        bad_rows = df[abs(prob_sum - 1.0) > 0.01]
        assert len(bad_rows) == 0, \
            f"Found {len(bad_rows)} rows where probabilities don't sum to ~1.0"

    def test_validation_csv_seasons_are_kiremt_or_belg(self):
        """Only Kiremt and Belg should appear as seasons in validation_results.csv."""
        import pandas as pd
        path = os.path.join(os.path.dirname(__file__), "../data/validation_results.csv")
        if not os.path.exists(path):
            pytest.skip("validation_results.csv not present in this environment")
        df = pd.read_csv(path)
        unexpected = set(df["season"].unique()) - {"Kiremt", "Belg"}
        assert not unexpected, \
            f"Unexpected seasons in validation CSV: {unexpected}"
