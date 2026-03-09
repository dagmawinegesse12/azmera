"""
Azmera — Seasonal Rainfall Forecast App
AI-powered drought early warning for Ethiopian farmers
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))
from forecaster import forecast, forecast_zone, get_zones_for_region, get_latest_indices, get_food_prices
from map_component import render_risk_map, get_all_forecasts
from chirps_anomaly import get_season_anomaly, get_latest_month_rainfall
from validation import render_validation_tab

try:
    from gee_features import render_gee_panel, init_gee
    GEE_AVAILABLE = True
except Exception:
    GEE_AVAILABLE = False

# ── Caching ───────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def cached_food_prices(region_key):
    return get_food_prices(region_key)

@st.cache_data(ttl=3600)
def cached_indices():
    return get_latest_indices()

@st.cache_data(ttl=3600)
def cached_all_forecasts(season_key):
    return get_all_forecasts(season_key, forecast)

@st.cache_data(ttl=86400)  # daily — parquet is static until models are retrained
def cached_seasonal_parquet(path):
    """Cache the historical parquet read — avoid re-reading on every button press."""
    try:
        return pd.read_parquet(path)
    except Exception as e:
        print(f"[Azmera] WARNING: Could not load seasonal parquet at {path}: {e}")
        return pd.DataFrame()

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Azmera — Ethiopia Rainfall Forecast",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Styling ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=Noto+Sans+Ethiopic:wght@400;600&display=swap');

* { font-family: 'Sora', sans-serif; }

.main { background-color: #080c14; }
.block-container { padding-top: 3rem; padding-bottom: 2rem; }

.verdict-card {
    border-radius: 20px;
    padding: 36px 40px;
    margin: 16px 0;
    position: relative;
    overflow: hidden;
}
.verdict-red {
    background: linear-gradient(135deg, #1a0a0a 0%, #2d1010 100%);
    border: 1px solid #c0392b;
    box-shadow: 0 0 40px rgba(192,57,43,0.3);
}
.verdict-yellow {
    background: linear-gradient(135deg, #1a150a 0%, #2d2310 100%);
    border: 1px solid #d4a017;
    box-shadow: 0 0 40px rgba(212,160,23,0.3);
}
.verdict-green {
    background: linear-gradient(135deg, #0a1a0a 0%, #102d10 100%);
    border: 1px solid #27ae60;
    box-shadow: 0 0 40px rgba(39,174,96,0.3);
}
.verdict-title {
    font-size: 2.2rem;
    font-weight: 700;
    margin: 0 0 8px 0;
    letter-spacing: -0.5px;
}
.verdict-subtitle {
    font-size: 1.0rem;
    opacity: 0.7;
    margin: 0;
}
.signal-pill {
    background: #0f1623;
    border: 1px solid #1e2a3d;
    border-radius: 14px;
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.signal-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #4a6080;
    font-weight: 600;
}
.signal-value {
    font-size: 1.1rem;
    font-weight: 600;
    color: #e0e8f0;
}
.signal-meaning {
    font-size: 0.82rem;
    color: #7a90a8;
    margin-top: 2px;
}
.advisory-card {
    background: #0f1623;
    border: 1px solid #1e2a3d;
    border-radius: 16px;
    padding: 24px 28px;
    margin: 8px 0;
}
.advisory-title {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #4a6080;
    font-weight: 600;
    margin-bottom: 16px;
}
.conf-bar-wrap {
    background: #1a2030;
    border-radius: 8px;
    height: 8px;
    margin: 8px 0 4px 0;
    overflow: hidden;
}
.conf-bar-fill {
    height: 100%;
    border-radius: 8px;
    transition: width 0.6s ease;
}
.section-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #4a6080;
    font-weight: 600;
    margin: 24px 0 12px 0;
}
.explainer {
    background: #0a0e18;
    border-left: 3px solid #4a6080;
    border-radius: 0 10px 10px 0;
    padding: 14px 18px;
    margin: 12px 0;
    color: #8a9ab0;
    font-size: 0.88rem;
    line-height: 1.6;
}
section[data-testid="stSidebar"] {
    background: #080c14;
    border-right: 1px solid #1a2030;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stRadio label {
    color: #7a90a8 !important;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 1px;
}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── Region data ───────────────────────────────────────────────────
REGIONS = {
    "Oromia":             (7.5081,  38.7651),
    "Amhara":             (11.5650, 38.0435),
    "Tigray":             (13.7771, 38.4387),
    "SNNPR":              (6.4523,  36.6913),
    "Sidama":             (6.6642,  38.5457),
    "South West":         (7.2000,  35.8000),
    "Afar":               (12.0363, 40.7727),
    "Somali":             (6.9295,  43.3290),
    "Gambela":            (7.6838,  34.3368),
    "Benishangul Gumz":   (10.5029, 35.4403),
    "Addis Ababa":        (8.9805,  38.7855),
    "Dire Dawa":          (9.6063,  42.0030),
    "Harari":             (9.2897,  42.1725),
}

SEASON_MONTHS = {
    "Kiremt": "June – September",
    "Belg":   "March – May",
    "OND":    "October – December",
    "Bega":   "January – February",
}

# ── Helpers ───────────────────────────────────────────────────────
def explain_enso(val):
    if val is None or val < -9000:
        return "⚪ Data unavailable", "No ENSO signal"
    if val > 1.5:
        return "🔴 Strong El Niño", "Historically reduces rainfall across Ethiopia"
    if val > 0.5:
        return "🟠 El Niño active", "May reduce rainfall — watch closely"
    if val < -1.5:
        return "🔵 Strong La Niña", "Historically brings mixed results by region"
    if val < -0.5:
        return "🔵 La Niña active", "Rainfall patterns vary — monitor closely"
    return "⚪ Neutral conditions", "No strong El Niño or La Niña signal"

def explain_iod(val):
    if val is None or abs(val) > 90:
        return "⚪ Data unavailable", "IOD data not available for this period"
    if val > 0.4:
        return "🟠 Positive IOD", "Indian Ocean warmer than normal — can reduce Oct–Dec rains"
    if val < -0.4:
        return "🔵 Negative IOD", "Indian Ocean cooler than normal — mixed impact"
    return "⚪ Neutral IOD", "Indian Ocean conditions are normal"

def explain_pdo(val):
    if val is None or abs(val) > 9:
        return "⚪ Data unavailable", "PDO data not available"
    if val > 0.5:
        return "🟠 Warm Pacific", "Amplifies El Niño drought risk when combined"
    if val < -0.5:
        return "🔵 Cool Pacific", "Can dampen El Niño effects slightly"
    return "⚪ Neutral Pacific", "Pacific long-term cycle is neutral"

# ── Globals (set in sidebar, used in main) ───────────────────────
zone_key = None
selected_zone = None

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 8px 0">
        <div style="font-size:2rem">🌾</div>
        <div style="font-size:1.4rem; font-weight:700; color:#e0e8f0;
                    letter-spacing:-0.5px; margin-top:4px">Azmera</div>
        <div style="font-size:0.8rem; color:#4a6080; margin-top:4px;
                    line-height:1.5">
            Seasonal rainfall forecasting<br>for Ethiopian farmers
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    region = st.selectbox("📍 Region", list(REGIONS.keys()), index=0)

    # ── Zone selector ─────────────────────────────────────────────
    _region_key = region.lower().replace(" ", "_")
    _zones = get_zones_for_region(_region_key)
    _zone_options = ["All zones (region-level)"] + [z["zone_display"] for z in _zones]
    if region in ("Sidama", "South West"):
        st.caption(
            "ℹ️ Sidama and South West share the SNNPR boundary on the risk map — "
            "zone forecasts use Southern Nations boundaries."
        )
    selected_zone = st.selectbox("🗺️ Zone", _zone_options, index=0)
    if selected_zone != "All zones (region-level)":
        zone_key = next((z["zone_key"] for z in _zones if z["zone_display"] == selected_zone), None)
    else:
        zone_key = None

    season_label = st.selectbox(
        "🌿 Season",
        [
            "Kiremt — Main rains (Jun–Sep)",
            "Belg — Short rains (Mar–May)",
            "OND — Short rains (Oct–Dec)",
            "Bega — Dry season rains (Jan–Feb)",
        ],
        index=0
    )
    if "Kiremt" in season_label:
        season_key = "Kiremt"
    elif "Belg" in season_label:
        season_key = "Belg"
    elif "OND" in season_label:
        season_key = "OND"
    else:
        season_key = "Bega"

    language = st.radio("🌐 Language", ["English", "አማርኛ Amharic"], index=0)

    st.write("")
    run = st.button("🔮 Generate Forecast", type="primary", use_container_width=True)

    st.divider()

    with st.expander("ℹ️ About Azmera"):
        st.markdown("""
        Azmera uses 42 years of climate data to forecast
        whether the upcoming planting season will be **dry,
        normal, or wet** — giving farmers time to prepare.

        **Data sources**
        - NASA satellite rainfall records
        - NOAA ocean temperature indices
        - 4 global climate signals
        - WFP live market prices

        **Validated against**
        - Kiremt LOOCV HSS 0.316 · rolling-origin HSS +0.063 (Phase D)
        - 2002 El Niño drought → 80% LOOCV detection rate
        - 1984 famine year → 56% LOOCV detection rate
        - 42 years · 1,092 verified forecasts (LOOCV)
        - ⚠️ See Validation tab for full skill context
        """)

# ── Main ──────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:8px">
    <span style="font-size:0.75rem; text-transform:uppercase;
                 letter-spacing:2px; color:#4a6080">
        SEASONAL OUTLOOK
    </span>
    <h1 style="font-size:2rem; font-weight:700; color:#e0e8f0;
               margin:4px 0 0 0; letter-spacing:-0.5px">
        Ethiopia Rainfall Forecast
    </h1>
</div>
""", unsafe_allow_html=True)

# ── Climate conditions strip ──────────────────────────────────────
try:
    indices  = cached_indices()
    enso_val = float(indices["enso"][-1]) if len(indices["enso"]) > 0 else None
    iod_val  = float(indices["iod"][-1])  if len(indices["iod"]) > 0  else None
    pdo_val  = float(indices["pdo"][-1])  if len(indices["pdo"]) > 0  else None

    if iod_val and (abs(iod_val) > 90): iod_val = None
    if pdo_val and (abs(pdo_val) > 9):  pdo_val = None

    enso_status, enso_meaning = explain_enso(enso_val)
    iod_status,  iod_meaning  = explain_iod(iod_val)
    pdo_status,  pdo_meaning  = explain_pdo(pdo_val)

    st.markdown('<p class="section-label">Current Ocean Conditions</p>',
                unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="signal-pill">
            <span class="signal-label">El Niño / La Niña (ENSO)</span>
            <span class="signal-value">{enso_status}</span>
            <span class="signal-meaning">{enso_meaning}</span>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="signal-pill">
            <span class="signal-label">Indian Ocean (IOD)</span>
            <span class="signal-value">{iod_status}</span>
            <span class="signal-meaning">{iod_meaning}</span>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="signal-pill">
            <span class="signal-label">Pacific Long-term (PDO)</span>
            <span class="signal-value">{pdo_status}</span>
            <span class="signal-meaning">{pdo_meaning}</span>
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.warning(f"Could not load climate conditions: {e}")

st.write("")

# ── Tabs ──────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Forecast", "🗺️ Risk Map", "🔬 Validation"])

# ── Tab 1: Forecast ───────────────────────────────────────────────
with tab1:

    # ── Tier 2: Monitoring-only for OND and Bega ──────────────────
    if run and season_key in ("OND", "Bega"):
        region_key = region.lower().replace(" ", "_")

        season_info = {
            "OND": {
                "months":  "October – December",
                "driver":  "IOD (Indian Ocean Dipole)",
                "regions": "Somali, SNNPR, Sidama, Dire Dawa",
                "note":    "OND is the main rainy season for southern and eastern Ethiopia. "
                           "Statistical forecast skill is currently insufficient for this season — "
                           "satellite monitoring is provided instead.",
            },
            "Bega": {
                "months":  "January – February",
                "driver":  "IOD + Atlantic SST",
                "regions": "Afar, Somali pastoralists",
                "note":    "Bega is a minor dry-season rain important for pastoralists in Afar and Somali. "
                           "Statistical forecast skill is currently insufficient — "
                           "satellite monitoring is provided instead.",
            },
        }
        info = season_info[season_key]

        st.markdown(f"""
        <div style="background:#0f1623; border:1px solid #d4a017;
                    border-left:4px solid #d4a017; border-radius:0 14px 14px 0;
                    padding:20px 24px; margin-bottom:24px">
            <div style="font-size:0.72rem; text-transform:uppercase;
                        letter-spacing:2px; color:#d4a017; margin-bottom:8px">
                🛰️ SATELLITE MONITORING MODE
            </div>
            <div style="font-size:1.1rem; font-weight:600; color:#e0e8f0; margin-bottom:8px">
                {season_key} Season ({info["months"]}) — {region}
            </div>
            <div style="color:#7a90a8; font-size:0.88rem; line-height:1.7">
                {info["note"]}<br><br>
                <b style="color:#c8d8e8">Primary climate driver:</b> {info["driver"]}<br>
                <b style="color:#c8d8e8">Most affected regions:</b> {info["regions"]}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Observed rainfall
        st.markdown('<p class="section-label">Observed Rainfall — Current Season</p>',
                    unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        with cc1:
            try:
                anomaly = get_season_anomaly(region_key, season_key)
                if anomaly:
                    a_color = {"Above Normal": "#27ae60", "Near Normal": "#d4a017",
                               "Below Normal": "#e74c3c"}.get(anomaly["status"], "#4a6080")
                    a_icon  = {"Above Normal": "💧", "Near Normal": "🌤️",
                               "Below Normal": "⚠️"}.get(anomaly["status"], "🌧️")
                    season_str = "Full Season" if anomaly["completed"] else "Season-to-date"
                    st.markdown(f"""
                    <div class="signal-pill">
                        <span class="signal-label">{anomaly["season"]} {anomaly["year"]} — {season_str}</span>
                        <span class="signal-value" style="color:{a_color}">{a_icon} {anomaly["total_mm"]}mm &nbsp;·&nbsp; {anomaly["anomaly_pct"]:+.1f}% vs baseline</span>
                        <span class="signal-meaning">{anomaly["status"]} &nbsp;·&nbsp; Baseline {anomaly["baseline_mean"]}mm (1991–2020 avg)</span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("Rainfall data not yet available for this season.")
            except Exception as e:
                st.caption(f"Rainfall anomaly unavailable: {e}")
        with cc2:
            try:
                latest = get_latest_month_rainfall(region_key)
                if latest:
                    st.markdown(f"""
                    <div class="signal-pill">
                        <span class="signal-label">Latest — {latest["label"]}</span>
                        <span class="signal-value">🌧️ {latest["rainfall"]}mm</span>
                        <span class="signal-meaning">Most recent CHIRPS observation &nbsp;·&nbsp; Source: CHIRPS v2.0</span>
                    </div>
                    """, unsafe_allow_html=True)
            except Exception as e:
                st.caption(f"Latest rainfall unavailable: {e}")

        # Historical chart
        st.markdown(f'<p class="section-label">Historical {season_key} Rainfall 1981–2022</p>',
                    unsafe_allow_html=True)
        try:
            DATA_PATH   = os.path.join(os.path.dirname(__file__), "../data/processed/seasonal_4seasons.parquet")
            seasonal_4s = cached_seasonal_parquet(DATA_PATH)
            region_hist = seasonal_4s[
                (seasonal_4s["region"] == region_key) &
                (seasonal_4s["season"] == season_key)
            ].copy()
            if not region_hist.empty:
                bar_colors = region_hist["target"].map({0: "#e74c3c", 1: "#d4a017", 2: "#27ae60"})
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=region_hist["year"], y=region_hist["spi"],
                    marker_color=bar_colors,
                    hovertemplate="<b>%{x}</b><br>%{customdata}<extra></extra>",
                    customdata=region_hist["target"].map(
                        {0: "⚠️ Drought year", 1: "🌤️ Normal year", 2: "✅ Good rains"})
                ))
                fig.add_hline(y=0,    line_color="#4a6080", line_width=1)
                fig.add_hline(y=-0.5, line_color="#e74c3c", line_dash="dot", line_width=1)
                fig.add_hline(y=0.5,  line_color="#27ae60", line_dash="dot", line_width=1)
                fig.update_layout(
                    plot_bgcolor="#080c14", paper_bgcolor="#080c14",
                    font=dict(color="#7a90a8", size=11), height=220,
                    margin=dict(l=10, r=10, t=10, b=30), showlegend=False,
                    xaxis=dict(gridcolor="#1a2030"), yaxis=dict(gridcolor="#1a2030"),
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Red=Below Normal · Yellow=Near Normal · Green=Above Normal")
            else:
                st.info("No historical data available for this region/season.")
        except Exception as e:
            st.info(f"Historical chart unavailable: {e}")

        # GEE satellite panel
        if GEE_AVAILABLE:
            render_gee_panel(region.strip())

        # Coming soon notice
        st.markdown("""
        <div style="background:#0a0e18; border-left:3px solid #4a6080;
                    border-radius:0 10px 10px 0; padding:14px 18px; margin-top:20px;
                    color:#8a9ab0; font-size:0.85rem; line-height:1.8">
            <b style="color:#c8d8e8">Statistical forecast in development</b><br>
            We are building a validated statistical model for this season.
            Improving OND and Bega forecast skill requires additional gridded spatial
            data and longer training records. Follow Azmera updates for when this launches.
        </div>
        """, unsafe_allow_html=True)

    # ── Tier 1: Full forecast for Kiremt and Belg ─────────────────
    elif run:
        region_key = region.lower().replace(" ", "_")

        try:
            if zone_key:
                with st.spinner(f"Analyzing climate signals for {selected_zone}, {region}..."):
                    result = forecast_zone(zone_key, selected_zone, region_key, season_key)
            else:
                with st.spinner(f"Analyzing climate signals for {region}..."):
                    result = forecast(region_key, season_key)
        except ValueError as e:
            # Raised for unsupported seasons — surface cleanly
            st.error(f"⚠️ {e}")
            st.stop()
        except Exception as e:
            import traceback
            print(f"[Azmera] Forecast error for {region}/{season_key}: {traceback.format_exc()}")
            st.error(
                f"🔴 Forecast generation failed for **{region}** ({season_key}).\n\n"
                f"Possible causes: missing model file, unavailable climate index data, "
                f"or network issue.\n\nTechnical detail: `{type(e).__name__}: {e}`"
            )
            st.stop()

        pred         = result["prediction"]
        conf         = result["confidence"]
        p_below      = result["prob_below"]
        p_near       = result["prob_near"]
        p_above      = result["prob_above"]
        is_fallback  = result.get("source") == "region_fallback"
        no_skill     = result.get("no_skill", False)
        release_tier = result.get("release_tier", "experimental")
        ro_hss_val   = result.get("ro_hss")

        location_label = f"{selected_zone}, {region}" if zone_key else region

        # ── Tier-based skill banner ───────────────────────────────
        # Shown BEFORE the verdict card. Suppressed tier is handled by the
        # no_skill panel below; experimental and full show different banners.
        if release_tier == "experimental":
            ro_str = f"Rolling-origin HSS {ro_hss_val:+.3f}" if ro_hss_val is not None else ""
            season_label = "Belg (Mar–May)" if season_key == "Belg" else "Kiremt (Jun–Sep)"
            st.markdown(f"""
            <div style="background:#0f1623; border:1px solid #d4a017;
                        border-left:4px solid #d4a017; border-radius:0 14px 14px 0;
                        padding:14px 18px; margin-bottom:16px">
                <div style="font-size:0.72rem; text-transform:uppercase;
                            letter-spacing:2px; color:#d4a017; margin-bottom:6px">
                    ⚠️ EXPERIMENTAL — MARGINAL FORECAST SKILL
                </div>
                <div style="color:#c8d8e8; font-size:0.88rem; line-height:1.7">
                    <b>{region} · {season_label}:</b> prospective skill score
                    <b>{ro_str}</b> — positive but below the validated threshold
                    (rolling-origin HSS ≥ 0.10). The ocean signal is detectable but weak.
                    <b style="color:#d4a017">Use alongside local knowledge and
                    official ICPAC / NMA advisories. Do not treat as a reliable
                    operational forecast.</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif release_tier == "full" and season_key == "Belg":
            ro_str = f"{ro_hss_val:+.3f}" if ro_hss_val is not None else ""
            st.markdown(f"""
            <div style="background:#071410; border:1px solid #1a5030;
                        border-left:4px solid #27ae60; border-radius:0 14px 14px 0;
                        padding:10px 18px; margin-bottom:16px">
                <div style="color:#7aaa88; font-size:0.82rem; line-height:1.6">
                    ✅ <b style="color:#4caf84">Validated Belg forecast</b> —
                    Rolling-origin HSS {ro_str} for {region} (prospective skill
                    over 27 unseen test years, Phase F). Still treat probabilistically —
                    no seasonal forecast is deterministic.
                </div>
            </div>
            """, unsafe_allow_html=True)
        # 'full' Kiremt: no banner (standard behavior)
        # 'suppressed': handled by no_skill panel below

        # ── No-skill (suppressed): show neutral panel, suppress verdict/advisory ──
        if no_skill:
            ro_str = f"rolling-origin HSS {ro_hss_val:+.3f}" if ro_hss_val is not None \
                     else "no prospective skill demonstrated"
            st.markdown(f"""
            <div style="background:#0d1520; border:1px solid #4a6080;
                        border-left:4px solid #6272a4; border-radius:0 14px 14px 0;
                        padding:20px 22px; margin-bottom:20px">
                <div style="font-size:0.72rem; text-transform:uppercase;
                            letter-spacing:2px; color:#6272a4; margin-bottom:8px">
                    📊 No Validated Forecast &nbsp;·&nbsp; {ro_str}
                </div>
                <div style="color:#c8d8e8; font-size:1.05rem; font-weight:600;
                            margin-bottom:10px">
                    {region} &nbsp;·&nbsp; {season_key} Season
                </div>
                <div style="color:#8a9ab8; font-size:0.88rem; line-height:1.8">
                    Rolling-origin validation — training on 1981–T and forecasting T+1
                    across 27 test years — showed negative prospective skill
                    (<b>{ro_str}</b>) for this region and season. The model performed
                    <i>worse than climatological chance</i> on unseen seasons.
                    Issuing a probabilistic forecast would be scientifically misleading.
                    <br><br>
                    <b style="color:#c8d8e8">Best available estimate:</b>
                    Treat each outcome as equally likely —
                    <b>~33% probability</b> for Below Normal,
                    Near Normal, and Above Normal rainfall.
                    <br><br>
                    <span style="color:#4a6080; font-size:0.8rem">
                        ℹ️ Observed CHIRPS satellite data (below) is valid and
                        shown for climate context.
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            # ── Fallback notice ───────────────────────────────────
            if zone_key and is_fallback:
                st.markdown(f"""
            <div style="background:#0f1623; border:1px solid #4a6080;
                        border-left:4px solid #4a6080; border-radius:0 10px 10px 0;
                        padding:12px 16px; margin-bottom:16px; font-size:0.85rem; color:#7a90a8">
                ⚠️ <b style="color:#c8d8e8">Zone-level model unavailable for {selected_zone}</b><br>
                The zone model did not meet the minimum skill threshold (HSS &gt; 0) —
                showing the <b style="color:#c8d8e8">{region} region forecast</b> instead.
                Zone-level detail requires sufficient historical signal.
            </div>
            """, unsafe_allow_html=True)

            # ── Verdict card ──────────────────────────────────────
            if pred == "Below Normal":
                verdict_class = "verdict-red"
                verdict_icon  = "⚠️"
                verdict_title = "Drought Risk — Prepare Now"
                verdict_color = "#e74c3c"
                verdict_msg   = f"Rainfall in {location_label} during {SEASON_MONTHS[season_key]} is likely to be below normal."
            elif pred == "Above Normal":
                verdict_class = "verdict-green"
                verdict_icon  = "✅"
                verdict_title = "Good Rains Likely"
                verdict_color = "#27ae60"
                verdict_msg   = f"Rainfall in {location_label} during {SEASON_MONTHS[season_key]} is likely to be above normal."
            else:
                verdict_class = "verdict-yellow"
                verdict_icon  = "🌤️"
                verdict_title = "Near Normal Season Expected"
                verdict_color = "#d4a017"
                verdict_msg   = f"Rainfall in {location_label} during {SEASON_MONTHS[season_key]} is likely to be close to average."

            st.markdown(f"""
        <div class="verdict-card {verdict_class}">
            <div class="verdict-title" style="color:{verdict_color}">
                {verdict_icon} {verdict_title}
            </div>
            <div class="verdict-subtitle">{verdict_msg}</div>
        </div>
        """, unsafe_allow_html=True)

            if conf > 0.55:
                signal_label = "🟢 Strong signal"
                signal_color = "#27ae60"
                signal_note  = "Ocean conditions clearly favour this outcome."
            elif conf > 0.45:
                signal_label = "🟡 Moderate signal"
                signal_color = "#d4a017"
                signal_note  = "Some uncertainty — multiple outcomes remain plausible."
            else:
                signal_label = "🔴 Weak signal"
                signal_color = "#e74c3c"
                signal_note  = "Climate conditions are mixed — all outcomes remain plausible."

            st.markdown(f"""
        <div class="explainer">
            <b style="color:{signal_color}">{signal_label}</b> — {signal_note}
            <div style="color:#4a6080; font-size:0.78rem; margin-top:8px">
                ⚠️ Signal strength reflects relative model confidence, not a calibrated
                probability estimate. See the Validation tab for skill context.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── CHIRPS Observed Rainfall ──────────────────────────────
        st.markdown('<p class="section-label">Observed Rainfall</p>', unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)

        with cc1:
            try:
                anomaly = get_season_anomaly(region_key, season_key)
                if anomaly:
                    a_color = {
                        "Above Normal": "#27ae60",
                        "Near Normal":  "#d4a017",
                        "Below Normal": "#e74c3c"
                    }.get(anomaly["status"], "#4a6080")
                    a_icon = {
                        "Above Normal": "💧",
                        "Near Normal":  "🌤️",
                        "Below Normal": "⚠️"
                    }.get(anomaly["status"], "🌧️")
                    season_str = "Full Season" if anomaly["completed"] else "Season-to-date"
                    st.markdown(f"""
                    <div class="signal-pill">
                        <span class="signal-label">{anomaly["season"]} {anomaly["year"]} — {season_str}</span>
                        <span class="signal-value" style="color:{a_color}">{a_icon} {anomaly["total_mm"]}mm &nbsp;·&nbsp; {anomaly["anomaly_pct"]:+.1f}% vs baseline</span>
                        <span class="signal-meaning">{anomaly["status"]} &nbsp;·&nbsp; Baseline {anomaly["baseline_mean"]}mm (1991–2020 avg)</span>
                    </div>
                    """, unsafe_allow_html=True)
            except Exception as e:
                st.caption(f"Rainfall anomaly unavailable: {e}")

        with cc2:
            try:
                latest = get_latest_month_rainfall(region_key)
                if latest:
                    st.markdown(f"""
                    <div class="signal-pill">
                        <span class="signal-label">Latest Available — {latest["label"]}</span>
                        <span class="signal-value">🌧️ {latest["rainfall"]}mm</span>
                        <span class="signal-meaning">Most recent CHIRPS observation &nbsp;·&nbsp; Source: CHIRPS v2.0</span>
                    </div>
                    """, unsafe_allow_html=True)
            except Exception as e:
                st.caption(f"Latest rainfall unavailable: {e}")

        st.write("")

        # ── Probability + Historical chart ────────────────────────
        # Skilled models: two columns (prob breakdown + history).
        # No-skill models: historical chart only, full width (probabilities
        # from a no-skill model carry no information above climatology).
        if no_skill:
            _hist_container = st.container()
        else:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown('<p class="section-label">Probability Breakdown</p>',
                            unsafe_allow_html=True)

                for label, prob, color, icon in [
                    ("Drought (Below Normal)",    p_below, "#e74c3c", "⚠️"),
                    ("Normal Season",             p_near,  "#d4a017", "🌤️"),
                    ("Good Rains (Above Normal)", p_above, "#27ae60", "✅"),
                ]:
                    pct = int(prob * 100)
                    st.markdown(f"""
                <div style="margin-bottom:14px">
                    <div style="display:flex; justify-content:space-between;
                                margin-bottom:5px">
                        <span style="color:#c8d8e8; font-size:0.9rem">
                            {icon} {label}
                        </span>
                        <span style="color:{color}; font-weight:600;
                                     font-size:0.9rem">{pct}%</span>
                    </div>
                    <div class="conf-bar-wrap">
                        <div class="conf-bar-fill"
                             style="width:{pct}%; background:{color}">
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            _hist_container = col2

        with _hist_container:
            st.markdown('<p class="section-label">Historical Rainfall for This Season</p>',
                        unsafe_allow_html=True)
            try:
                DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/processed/seasonal_enriched.parquet")
                seasonal_v3 = cached_seasonal_parquet(DATA_PATH)

                region_hist = seasonal_v3[
                    (seasonal_v3["region"] == region_key) &
                    (seasonal_v3["season"] == season_key)
                ].copy()

                bar_colors = region_hist["target"].map(
                    {0: "#e74c3c", 1: "#d4a017", 2: "#27ae60"}
                )

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=region_hist["year"],
                    y=region_hist["spi"],
                    marker_color=bar_colors,
                    hovertemplate="<b>%{x}</b><br>%{customdata}<extra></extra>",
                    customdata=region_hist["target"].map(
                        {0: "⚠️ Drought year",
                         1: "🌤️ Normal year",
                         2: "✅ Good rains"}
                    )
                ))
                fig.add_hline(y=0,    line_color="#4a6080", line_width=1)
                fig.add_hline(y=-0.5, line_color="#e74c3c", line_dash="dot", line_width=1)
                fig.add_hline(y=0.5,  line_color="#27ae60", line_dash="dot", line_width=1)

                fig.update_layout(
                    xaxis_title="Year",
                    yaxis_title="Rainfall anomaly",
                    plot_bgcolor="#080c14",
                    paper_bgcolor="#080c14",
                    font=dict(color="#7a90a8", size=11),
                    height=220,
                    margin=dict(l=10, r=10, t=10, b=30),
                    showlegend=False,
                    xaxis=dict(gridcolor="#1a2030"),
                    yaxis=dict(gridcolor="#1a2030"),
                )
                st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.info("Historical chart unavailable")

        # ── Farmer advisory (skilled models only) ────────────────
        # Suppressed for no-skill models: an advisory tied to a
        # scientifically-invalid forecast creates false confidence.
        if not no_skill:
            st.markdown('<p class="section-label">What Should Farmers Do?</p>',
                        unsafe_allow_html=True)

            advisory_text = result["advisory_am"] if "አማርኛ" in language \
                            else result["advisory_en"]

            lines = [l.strip() for l in advisory_text.split("\n") if l.strip()]

            advisory_items = "".join([
                f'<div style="margin-bottom:14px; color:#c8d8e8; font-size:0.97rem; line-height:1.6">{line}</div>'
                for line in lines if line.strip()
            ])

            st.markdown(f"""
        <div class="advisory-card">
            <div class="advisory-title">
                AI-Generated Advisory · {region} · {season_key} Season
            </div>
            {advisory_items}
            <div style="margin-top:16px; padding-top:12px; border-top:1px solid #1e2a3d;
                        color:#4a6080; font-size:0.75rem; line-height:1.5">
                ⚠️ AI-generated — not reviewed by agronomists. Crop recommendations may not
                reflect local varieties or market conditions. Consult local agricultural
                extension officers before making planting decisions.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── WFP Food Prices ───────────────────────────────────────
        st.markdown('<p class="section-label">📊 Current Market Prices (WFP Data)</p>',
                    unsafe_allow_html=True)

        with st.spinner("Loading market prices..."):
            prices = cached_food_prices(region_key)

        if prices:
            cols = st.columns(len(prices))
            for i, p in enumerate(prices):
                with cols[i]:
                    st.markdown(f"""
                    <div class="signal-pill" style="text-align:center">
                        <span class="signal-label">{p['crop']}</span>
                        <span class="signal-value" style="font-size:1.3rem">
                            {p['price_etb']:,.0f}
                        </span>
                        <span class="signal-meaning">ETB / quintal (100kg)</span>
                        <span style="font-size:1.1rem">{p['trend']}</span>
                        <span class="signal-meaning">{p['trend_str']}</span>
                    </div>
                    """, unsafe_allow_html=True)

            is_regional = prices[0].get("is_regional", True) if prices else True
            source_note = (
                f"📡 Source: WFP VAM / HDX — {prices[0]['region']} market prices. 1 quintal = 100kg."
                if is_regional else
                "📡 Source: WFP VAM / HDX — <b style='color:#d4a017'>National proxy data</b> (no regional prices available for this area). 1 quintal = 100kg."
            )
            st.markdown(f"""
            <div style="color:#3a4a5a; font-size:0.75rem; margin-top:8px">
                {source_note}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Market price data temporarily unavailable.")

        # ── GEE Satellite Panel ───────────────────────────────────
        if GEE_AVAILABLE:
            render_gee_panel(region.strip())

        # ── Disclaimer ────────────────────────────────────────────
        st.markdown("""
        <div style="color:#3a4a5a; font-size:0.78rem; margin-top:20px;
                    text-align:center; line-height:1.6">
            Azmera is an early warning tool. Forecasts are probabilistic
            and should be used alongside local knowledge and official advisories
            from ICPAC and Ethiopia's National Meteorological Institute (NMA).
        </div>
        """, unsafe_allow_html=True)

    else:
        # ── Default landing state ─────────────────────────────────
        st.markdown("""
        <div style="text-align:center; padding:48px 0 32px 0">
            <div style="font-size:3.5rem; margin-bottom:16px">🌾</div>
            <h2 style="color:#c8d8e8; font-weight:600;
                       letter-spacing:-0.5px; margin-bottom:8px">
                Select a region to get started
            </h2>
            <p style="color:#4a6080; font-size:0.95rem; max-width:480px;
                      margin:0 auto; line-height:1.7">
                Choose your region and farming season from the sidebar,
                then click <b style="color:#7a90a8">Generate Forecast</b>
                to see the AI-powered seasonal outlook.
            </p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            <div class="signal-pill" style="text-align:center; padding:24px">
                <div style="font-size:1.8rem; margin-bottom:8px">📡</div>
                <div style="color:#c8d8e8; font-weight:600;
                            margin-bottom:6px">4 Climate Signals</div>
                <div style="color:#4a6080; font-size:0.85rem">
                    ENSO, IOD, PDO and Atlantic SST
                    analyzed together
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class="signal-pill" style="text-align:center; padding:24px">
                <div style="font-size:1.8rem; margin-bottom:8px">📊</div>
                <div style="color:#c8d8e8; font-weight:600;
                            margin-bottom:6px">42 Years of Data</div>
                <div style="color:#4a6080; font-size:0.85rem">
                    Trained on 1981–2022 rainfall
                    records across 13 regions
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown("""
            <div class="signal-pill" style="text-align:center; padding:24px">
                <div style="font-size:1.8rem; margin-bottom:8px">🗣️</div>
                <div style="color:#c8d8e8; font-weight:600;
                            margin-bottom:6px">Amharic Advisory</div>
                <div style="color:#4a6080; font-size:0.85rem">
                    AI-generated farmer guidance
                    in English and Amharic
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.write("")
        if os.path.exists("../docs/validation_chart.png"):
            st.markdown('<p class="section-label">Model Validation — Oromia 1981–2024</p>',
                        unsafe_allow_html=True)
            st.image("../docs/validation_chart.png",
                     caption="Azmera correctly flagged all 4 drought-affected regions during Ethiopia's worst drought in 50 years (2015)",
                     use_container_width=True)

# ── Tab 2: Risk Map ───────────────────────────────────────────────
with tab2:
    st.markdown('<p class="section-label">Seasonal Forecast Risk — All Regions</p>',
                unsafe_allow_html=True)

    if "drill_region" not in st.session_state:
        st.session_state["drill_region"] = None
    if "last_map_region" not in st.session_state:
        st.session_state["last_map_region"] = None

    # Reset to Ethiopia overview when user switches region in sidebar
    if region != st.session_state["last_map_region"]:
        st.session_state["drill_region"] = None
        st.session_state["last_map_region"] = region

    # Drill into zone view only when user clicks Generate Forecast with a zone selected
    if run and zone_key:
        st.session_state["drill_region"] = region
    drill_region = st.session_state["drill_region"]

    if not run:
        st.markdown("""
        <div style="background:#0a0e18; border:1px solid #1e2a3d; border-radius:10px;
                    padding:12px 18px; margin-bottom:12px; color:#4a6080;
                    font-size:0.85rem; text-align:center">
            🔮 Click <b style="color:#7a90a8">Generate Forecast</b> in the sidebar
            to load forecasts on the map
        </div>
        """, unsafe_allow_html=True)

    with st.spinner("Loading forecasts..."):
        all_forecasts = cached_all_forecasts(season_key) if run else {}

    clicked_region, clicked_zone = render_risk_map(
        all_forecasts,
        selected_region=st.session_state.get("drill_region"),
        selected_zone=selected_zone if zone_key else None,
        season_key=season_key,
        forecaster_fn=forecast_zone,
    )

    if clicked_region and clicked_region != drill_region:
        st.session_state["drill_region"] = clicked_region
        st.rerun()

# ── Tab 3: Validation ─────────────────────────────────────────────
with tab3:
    render_validation_tab()
