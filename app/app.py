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
    selected_zone = st.selectbox("🗺️ Zone", _zone_options, index=0)
    if selected_zone != "All zones (region-level)":
        zone_key = next((z["zone_key"] for z in _zones if z["zone_display"] == selected_zone), None)
    else:
        zone_key = None

    season_label = st.selectbox(
        "🌿 Season",
        ["Kiremt — Main rains (Jun–Sep)", "Belg — Short rains (Mar–May)"],
        index=0
    )
    season_key = "Kiremt" if "Kiremt" in season_label else "Belg"

    language = st.radio("🌐 Language", ["English", "አማርኛ Amharic"], index=0)

    st.write("")
    run = st.button("🔮 Generate Forecast", type="primary", use_container_width=True)

    st.divider()

    with st.expander("ℹ️ About Azmera"):
        st.markdown("""
        Azmera uses 44 years of climate data to forecast
        whether the upcoming planting season will be **dry,
        normal, or wet** — giving farmers time to prepare.

        **Data sources**
        - NASA satellite rainfall records
        - NOAA ocean temperature indices
        - 4 global climate signals
        - WFP live market prices

        **Validated against**
        - 2002–2005 drought (99% accuracy)
        - 2009 drought (82% accuracy)
        - 2015 El Niño drought (correctly flagged all 4 affected regions)
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
tab1, tab2 = st.tabs(["📊 Forecast", "🗺️ Risk Map"])

# ── Tab 1: Forecast ───────────────────────────────────────────────
with tab1:
    if run:
        region_key = region.lower().replace(" ", "_")

        if zone_key:
            with st.spinner(f"Analyzing climate signals for {selected_zone}, {region}..."):
                result = forecast_zone(zone_key, selected_zone, region_key, season_key)
        else:
            with st.spinner(f"Analyzing climate signals for {region}..."):
                result = forecast(region_key, season_key)

        pred    = result["prediction"]
        conf    = result["confidence"]
        p_below = result["prob_below"]
        p_near  = result["prob_near"]
        p_above = result["prob_above"]

        location_label = f"{selected_zone}, {region}" if zone_key else region

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

        conf_pct   = int(conf * 100)
        conf_color = "#27ae60" if conf > 0.6 else \
                     "#d4a017" if conf > 0.45 else "#e74c3c"

        st.markdown(f"""
        <div class="explainer">
            <b style="color:#c8d8e8">Model confidence: {conf_pct}%</b>
            {"— High confidence. Ocean signals are strong and consistent." if conf > 0.6 else
             "— Moderate confidence. Some uncertainty in the forecast." if conf > 0.45 else
             "— Lower confidence. Climate signals are mixed — prepare for variability."}
            <div class="conf-bar-wrap" style="margin-top:10px">
                <div class="conf-bar-fill"
                     style="width:{conf_pct}%; background:{conf_color}"></div>
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

        with col2:
            st.markdown('<p class="section-label">Historical Rainfall for This Season</p>',
                        unsafe_allow_html=True)
            try:
                DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/processed/seasonal_enriched.parquet")
                seasonal_v3 = pd.read_parquet(DATA_PATH)

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

        # ── Farmer advisory ───────────────────────────────────────
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

            st.markdown("""
            <div style="color:#3a4a5a; font-size:0.75rem; margin-top:8px">
                📡 Source: WFP VAM / HDX — Ethiopia market prices.
                1 quintal = 100kg. Prices vary by market and region.
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
                            margin-bottom:6px">44 Years of Data</div>
                <div style="color:#4a6080; font-size:0.85rem">
                    Trained on 1981–2024 rainfall
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

    # Always sync map drill-down to sidebar region
    st.session_state["drill_region"] = region
    drill_region = region

    with st.spinner("Loading forecasts..."):
        all_forecasts = cached_all_forecasts(season_key)

    clicked_region, clicked_zone = render_risk_map(
        all_forecasts,
        selected_region=drill_region,
        selected_zone=selected_zone if zone_key else None,
        season_key=season_key,
        forecaster_fn=forecast_zone,
    )

    if clicked_region and clicked_region != drill_region:
        st.session_state["drill_region"] = clicked_region
        st.rerun()