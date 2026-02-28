"""
Azmera — Ethiopia Risk Map
Clickable choropleth map with region → zone drill-down.
"""

import json
import os
import folium
import pandas as pd
from streamlit_folium import st_folium
import streamlit as st

# ── Paths ─────────────────────────────────────────────────────────
BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
REGIONS_GEOJSON  = os.path.join(BASE_DIR, "../data/ethiopia_regions.geojson")
ZONES_GEOJSON    = os.path.join(BASE_DIR, "../data/ethiopia_zones.geojson")
CENTROIDS_CSV    = os.path.join(BASE_DIR, "../data/zone_centroids.csv")

# ── GeoJSON name → Azmera region name ────────────────────────────
GEOJSON_TO_AZMERA = {
    "Tigray":                        "Tigray",
    "Afar":                          "Afar",
    "Amhara":                        "Amhara",
    "Oromia":                        "Oromia",
    "Somali":                        "Somali",
    "Benshangul-Gumaz":              "Benishangul Gumz",
    "SouthernNations,Nationalities": "SNNPR",
    "GambelaPeoples":                "Gambela",
    "HarariPeople":                  "Harari",
    "DireDawa":                      "Dire Dawa",
    "AddisAbeba":                    "Addis Ababa",
}

AZMERA_TO_GEOJSON_REGION = {v: k for k, v in GEOJSON_TO_AZMERA.items()}

GEOJSON_TO_CENTROID_REGION = {
    "Tigray":                        "tigray",
    "Afar":                          "afar",
    "Amhara":                        "amhara",
    "Oromia":                        "oromia",
    "Somali":                        "somali",
    "Benshangul-Gumaz":              "benshangul_gumaz",
    "SouthernNations,Nationalities": "southernnationsnationalities",
    "GambelaPeoples":                "gambelapeoples",
    "HarariPeople":                  "hararipeople",
    "DireDawa":                      "diredawa",
    "AddisAbeba":                    "addisabeba",
}

RISK_COLORS = {
    "Below Normal": "#e05252",
    "Near Normal":  "#f0c040",
    "Above Normal": "#4caf84",
    "unknown":      "#2a3a4a",
}

# ── Load GeoJSONs ─────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def load_regions_geojson():
    with open(REGIONS_GEOJSON) as f:
        return json.load(f)

@st.cache_data(ttl=86400)
def load_zones_geojson():
    with open(ZONES_GEOJSON) as f:
        return json.load(f)

@st.cache_data(ttl=86400)
def load_centroids():
    return pd.read_csv(CENTROIDS_CSV)

# ── Get bounding box for a region ────────────────────────────────
def get_region_bounds(region_geojson_name):
    """Compute bounding box from GeoJSON coordinates — no shapely needed."""
    try:
        geojson = load_regions_geojson()
        for feature in geojson["features"]:
            if feature["properties"].get("NAME_1") != region_geojson_name:
                continue
            coords = []
            def extract_coords(geom):
                t = geom["type"]
                if t == "Polygon":
                    for ring in geom["coordinates"]:
                        coords.extend(ring)
                elif t == "MultiPolygon":
                    for poly in geom["coordinates"]:
                        for ring in poly:
                            coords.extend(ring)
            extract_coords(feature["geometry"])
            if not coords:
                return None
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            return [[min(lats), min(lons)], [max(lats), max(lons)]]
    except Exception as e:
        print(f"bounds error: {e}")
        return None

# ── Get zone forecasts for a region ──────────────────────────────
@st.cache_data(ttl=3600)
def get_zone_forecasts_cached(region_geojson_name, season_key):
    """Cached placeholder — actual forecasts injected at render time."""
    return {}

@st.cache_data(ttl=3600, show_spinner=False)
def get_zone_forecasts(region_geojson_name, season_key):
    """Cached zone forecasts — runs once per region/season, then reuses."""
    import pandas as pd
    from forecaster import forecast_zone
    centroids       = pd.read_csv(CENTROIDS_CSV)
    centroid_region = GEOJSON_TO_CENTROID_REGION.get(region_geojson_name, "")
    region_zones    = centroids[centroids["region_key"] == centroid_region]
    results = {}
    for _, zone in region_zones.iterrows():
        try:
            result = forecast_zone(zone["zone_key"], zone["zone_display"],
                                   zone["region_key"], season_key, fast=True)
            results[zone["zone_display"]] = result
        except Exception as e:
            print(f"Zone error {zone['zone_key']}: {e}")
    return results

# ── Legend ────────────────────────────────────────────────────────
def _add_legend(m):
    legend_html = """
    <div style="position:fixed;bottom:20px;left:20px;z-index:1000;
                background:#1a2a3a;padding:12px 16px;border-radius:8px;
                border:1px solid #2a3a4a;font-family:sans-serif;">
        <div style="color:#c8d8e8;font-size:12px;font-weight:600;margin-bottom:8px;">
            Seasonal Forecast
        </div>
        <div style="display:flex;align-items:center;margin-bottom:5px">
            <div style="width:14px;height:14px;background:#4caf84;border-radius:3px;margin-right:8px"></div>
            <span style="color:#c8d8e8;font-size:11px">Above Normal</span>
        </div>
        <div style="display:flex;align-items:center;margin-bottom:5px">
            <div style="width:14px;height:14px;background:#f0c040;border-radius:3px;margin-right:8px"></div>
            <span style="color:#c8d8e8;font-size:11px">Near Normal</span>
        </div>
        <div style="display:flex;align-items:center;margin-bottom:5px">
            <div style="width:14px;height:14px;background:#e05252;border-radius:3px;margin-right:8px"></div>
            <span style="color:#c8d8e8;font-size:11px">Below Normal</span>
        </div>
        <div style="display:flex;align-items:center">
            <div style="width:14px;height:14px;background:#2a3a4a;border-radius:3px;margin-right:8px"></div>
            <span style="color:#c8d8e8;font-size:11px">No Forecast</span>
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

# ── Region map ────────────────────────────────────────────────────
def render_region_map(forecast_results, selected_region=None):
    geojson = load_regions_geojson()

    def get_color(feature):
        geo_name   = feature["properties"].get("NAME_1", "")
        azmera     = GEOJSON_TO_AZMERA.get(geo_name, "")
        prediction = forecast_results.get(azmera, {}).get("prediction", "unknown")
        return RISK_COLORS.get(prediction, RISK_COLORS["unknown"])

    m = folium.Map(
        location=[9.0, 40.0],
        zoom_start=5,
        tiles="CartoDB dark_matter",
        scrollWheelZoom=False,
    )

    folium.GeoJson(
        geojson,
        name="Regions",
        style_function=lambda f: {
            "fillColor":   get_color(f),
            "color":       "#1a2a3a",
            "weight":      1.5,
            "fillOpacity": 0.75,
        },
        highlight_function=lambda f: {
            "fillColor":   get_color(f),
            "color":       "#ffffff",
            "weight":      2.5,
            "fillOpacity": 0.9,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["NAME_1"],
            aliases=["Region:"],
            style="background-color:#1a2a3a;color:#c8d8e8;font-family:sans-serif;font-size:13px;padding:6px;",
        ),
    ).add_to(m)

    # Dashed outline for selected region
    if selected_region:
        geo_name = AZMERA_TO_GEOJSON_REGION.get(selected_region)
        if geo_name:
            for feature in geojson["features"]:
                if feature["properties"].get("NAME_1") == geo_name:
                    folium.GeoJson(
                        feature,
                        style_function=lambda x: {
                            "fillColor":   "transparent",
                            "color":       "#ffffff",
                            "weight":      3,
                            "fillOpacity": 0,
                            "dashArray":   "5,5",
                        },
                    ).add_to(m)

    _add_legend(m)
    output = st_folium(m, width="100%", height=500, key="region_map",
                       returned_objects=["last_object_clicked_tooltip"])

    clicked = None
    if output and output.get("last_object_clicked_tooltip"):
        raw = output["last_object_clicked_tooltip"]
        if isinstance(raw, str):
            clicked = GEOJSON_TO_AZMERA.get(raw.strip(), raw.strip())
    return clicked

# ── Zone map ──────────────────────────────────────────────────────
def render_zone_map(region_display, region_geojson_name, zone_forecasts, selected_zone=None):
    zones_geojson = load_zones_geojson()

    region_features = {
        "type": "FeatureCollection",
        "features": [
            f for f in zones_geojson["features"]
            if f["properties"].get("NAME_1") == region_geojson_name
        ]
    }

    if not region_features["features"]:
        st.warning(f"No zone boundaries for {region_display}")
        return None

    def get_zone_color(feature):
        zone_name  = feature["properties"].get("NAME_2", "")
        prediction = zone_forecasts.get(zone_name, {}).get("prediction", "unknown")
        return RISK_COLORS.get(prediction, RISK_COLORS["unknown"])

    bounds = get_region_bounds(region_geojson_name)
    # Default center if bounds unavailable
    location = [9.0, 40.0]
    zoom = 6
    if bounds:
        location = [
            (bounds[0][0] + bounds[1][0]) / 2,
            (bounds[0][1] + bounds[1][1]) / 2,
        ]
    m = folium.Map(
        location=location,
        zoom_start=zoom,
        tiles="CartoDB dark_matter",
        scrollWheelZoom=False,
    )
    if bounds:
        m.fit_bounds(bounds)

    folium.GeoJson(
        region_features,
        name="Zones",
        style_function=lambda f: {
            "fillColor":   get_zone_color(f),
            "color":       "#1a2a3a",
            "weight":      1.5,
            "fillOpacity": 0.75,
        },
        highlight_function=lambda f: {
            "fillColor":   get_zone_color(f),
            "color":       "#ffffff",
            "weight":      2.5,
            "fillOpacity": 0.9,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["NAME_2"],
            aliases=["Zone:"],
            style="background-color:#1a2a3a;color:#c8d8e8;font-family:sans-serif;font-size:13px;padding:6px;",
        ),
    ).add_to(m)

    if selected_zone:
        for feature in region_features["features"]:
            if feature["properties"].get("NAME_2") == selected_zone:
                folium.GeoJson(
                    feature,
                    style_function=lambda x: {
                        "fillColor":   "transparent",
                        "color":       "#ffffff",
                        "weight":      3,
                        "fillOpacity": 0,
                        "dashArray":   "5,5",
                    },
                ).add_to(m)

    _add_legend(m)
    output = st_folium(m, width="100%", height=500, key="zone_map",
                       returned_objects=["last_object_clicked_tooltip"])

    clicked = None
    if output and output.get("last_object_clicked_tooltip"):
        raw = output["last_object_clicked_tooltip"]
        if isinstance(raw, str):
            clicked = raw.strip()
    return clicked

# ── Main render (called from app.py) ─────────────────────────────
def render_risk_map(forecast_results, selected_region=None, selected_zone=None,
                    season_key="Kiremt", forecaster_fn=None):
    """
    Region view by default.
    Drills into zone view when a region is selected in sidebar or clicked.
    """
    # Resolve selected_region to a proper display name
    geo_region_name = AZMERA_TO_GEOJSON_REGION.get(selected_region, "") if selected_region else ""
    in_zone_view    = bool(geo_region_name)

    if in_zone_view:
        # ── Zone view ─────────────────────────────────────────────
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("← Ethiopia", key="back_btn"):
                st.session_state["drill_region"] = None
                st.rerun()
        with col2:
            st.markdown(f"**🗺️ {selected_region} — Zone Forecast**")

        with st.spinner(f"Loading {selected_region} zone forecasts..."):
            zone_forecasts = get_zone_forecasts(geo_region_name, season_key)

        clicked_zone = render_zone_map(selected_region, geo_region_name,
                                       zone_forecasts, selected_zone=selected_zone)

        if clicked_zone:
            st.success(f"📍 **{clicked_zone}** — select it in the sidebar Zone dropdown for a full forecast.")

        # Zone cards
        if zone_forecasts:
            st.markdown('<p style="font-size:0.72rem;text-transform:uppercase;letter-spacing:2px;color:#4a6080;font-weight:600;margin:16px 0 8px 0">All Zone Forecasts</p>', unsafe_allow_html=True)
            cols = st.columns(3)
            for i, (zone_name, result) in enumerate(sorted(zone_forecasts.items())):
                pred  = result.get("prediction", "Unknown")
                conf  = result.get("confidence", 0)
                cv    = result.get("cv_accuracy", None)
                color = {"Below Normal": "#e05252", "Near Normal": "#f0c040",
                         "Above Normal": "#4caf84"}.get(pred, "#4a6080")
                cv_str = f"CV {cv:.0%}" if cv else "region model"
                with cols[i % 3]:
                    st.markdown(f"""
                    <div style="background:#0f1623;border:1px solid #1e2a3d;border-radius:10px;
                                padding:10px 14px;margin-bottom:8px">
                        <div style="color:#7a90a8;font-size:0.72rem;margin-bottom:4px">{zone_name}</div>
                        <div style="color:{color};font-weight:600;font-size:0.9rem">{pred}</div>
                        <div style="color:#4a6080;font-size:0.7rem">{conf:.0%} · {cv_str}</div>
                    </div>
                    """, unsafe_allow_html=True)

        return None, clicked_zone

    else:
        # ── Region view ───────────────────────────────────────────
        st.caption("Click a region to see zone-level forecasts")
        clicked_region = render_region_map(forecast_results, selected_region)

        if clicked_region:
            st.session_state["drill_region"] = clicked_region
            st.success(f"📍 You clicked **{clicked_region}** — select it in the sidebar to drill into zones.")

        return clicked_region, None


# ── get_all_forecasts ─────────────────────────────────────────────
def get_all_forecasts(season_key: str, forecaster_fn) -> dict:
    REGIONS = [
        "tigray", "afar", "amhara", "oromia", "somali",
        "benishangul_gumz", "snnpr", "gambela", "harari",
        "dire_dawa", "addis_ababa",
    ]
    REGION_DISPLAY = {
        "tigray":           "Tigray",
        "afar":             "Afar",
        "amhara":           "Amhara",
        "oromia":           "Oromia",
        "somali":           "Somali",
        "benishangul_gumz": "Benishangul Gumz",
        "snnpr":            "SNNPR",
        "gambela":          "Gambela",
        "harari":           "Harari",
        "dire_dawa":        "Dire Dawa",
        "addis_ababa":      "Addis Ababa",
    }
    results = {}
    for key in REGIONS:
        try:
            result = forecaster_fn(key, season_key, fast=True)
            results[REGION_DISPLAY[key]] = result
        except Exception:
            pass
    return results