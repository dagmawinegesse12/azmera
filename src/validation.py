"""
Azmera — Model Validation Tab
Shows leave-one-out cross-validation results, HSS, reliability diagram,
and key drought year performance. Standard WMO/ICPAC verification approach.
"""

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from sklearn.metrics import confusion_matrix
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_PATH = os.path.join(BASE_DIR, "../data/validation_results.csv")

LABEL_MAP  = {0: "Below Normal", 1: "Near Normal", 2: "Above Normal"}
COLOR_MAP  = {0: "#e74c3c", 1: "#d4a017", 2: "#27ae60"}
REGION_DISPLAY = {
    "addis_ababa":     "Addis Ababa",
    "afar":            "Afar",
    "amhara":          "Amhara",
    "benishangul_gumz":"Benishangul-Gumz",
    "dire_dawa":       "Dire Dawa",
    "gambela":         "Gambela",
    "harari":          "Harari",
    "oromia":          "Oromia",
    "sidama":          "Sidama",
    "snnpr":           "SNNPR",
    "somali":          "Somali",
    "south_west":      "South West",
    "tigray":          "Tigray",
}

DROUGHT_YEARS = {
    1984: "Worst famine of the 20th century",
    1987: "Widespread drought",
    1991: "Drought + political crisis",
    1994: "Localized severe drought",
    2002: "Major food crisis, 11M affected",
    2003: "Continued drought",
    2009: "La Niña drought",
    2015: "Record El Niño drought",
    2016: "Continued El Niño impact",
}


# These are the actual columns in data/validation_results.csv
# NOTE: hss is NOT a column in the CSV — it is computed on-the-fly by compute_hss()
_RESULTS_COLUMNS = ["region", "season", "year", "actual", "predicted",
                    "correct", "prob_below", "prob_near", "prob_above"]


@st.cache_data
def load_results():
    try:
        return pd.read_csv(RESULTS_PATH)
    except FileNotFoundError:
        print(f"[Azmera] WARNING: {RESULTS_PATH} not found — validation tab will show placeholder.")
        return pd.DataFrame(columns=_RESULTS_COLUMNS)
    except Exception as e:
        print(f"[Azmera] WARNING: Could not load validation results: {e}")
        return pd.DataFrame(columns=_RESULTS_COLUMNS)


def compute_hss(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
    n        = cm.sum()
    correct  = np.diag(cm).sum()
    expected = sum(cm[i,:].sum() * cm[:,i].sum() for i in range(3)) / n
    return (correct - expected) / (n - expected), cm


def bootstrap_hss_ci(y_true, y_pred, n_bootstrap=1000, ci=0.95, seed=42):
    """
    Bootstrap confidence interval for HSS.
    Resamples (y_true, y_pred) pairs with replacement n_bootstrap times.
    Returns (lower_bound, upper_bound) at the requested CI level.

    With n=1,092 pairs (42 years × 13 regions × 2 seasons), typical 95% CI
    width is ±0.05–0.08 on the aggregate HSS. Per-region CIs are wider
    (n≈42 per region/season, CI width ≈ ±0.13–0.16).
    """
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    n = len(y_true)
    hss_samples = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        yt, yp = y_true[idx], y_pred[idx]
        if len(np.unique(yt)) < 2:
            continue
        h, _ = compute_hss(yt, yp)
        hss_samples.append(h)
    alpha = (1 - ci) / 2
    return float(np.quantile(hss_samples, alpha)), float(np.quantile(hss_samples, 1 - alpha))


def render_validation_tab():
    df = load_results()

    # Guard: validation_results.csv missing or unreadable
    if df.empty:
        st.warning(
            "⚠️ **Validation data unavailable.** "
            "The file `data/validation_results.csv` could not be loaded. "
            "Run `scripts/build_region_models.py` to regenerate it, "
            "then restart the app.",
            icon="⚠️",
        )
        return

    st.markdown("""
    <div style="margin-bottom:24px">
        <span style="font-size:0.75rem; text-transform:uppercase;
                     letter-spacing:2px; color:#4a6080">
            MODEL VERIFICATION
        </span>
        <h2 style="font-size:1.6rem; font-weight:700; color:#e0e8f0;
                   margin:4px 0 8px 0; letter-spacing:-0.5px">
            How Accurate is Azmera?
        </h2>
        <p style="color:#7a90a8; font-size:0.9rem; max-width:700px; line-height:1.7">
            All results below use <b style="color:#c8d8e8">leave-one-out cross-validation</b> —
            for each year, the model was retrained on all other years and tested on the
            held-out year. This is the standard WMO/ICPAC approach for honest forecast verification.
            No year was ever used to both train and test.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Top metrics row ───────────────────────────────────────────
    hss_all, cm_all = compute_hss(df['actual'], df['predicted'])
    accuracy        = df['correct'].mean()

    hss_belg,   _ = compute_hss(
        df[df['season']=='Belg']['actual'],
        df[df['season']=='Belg']['predicted']
    )
    hss_kiremt, _ = compute_hss(
        df[df['season']=='Kiremt']['actual'],
        df[df['season']=='Kiremt']['predicted']
    )

    drought_df   = df[df['actual'] == 0]
    drought_hit  = drought_df['correct'].mean()

    col1, col2, col3, col4 = st.columns(4)

    def metric_card(col, label, value, subtext, color="#e0e8f0", ci_text=None):
        ci_html = (
            f'<div style="font-size:0.7rem; color:#4a6080; margin-top:6px; '
            f'font-style:italic">{ci_text}</div>'
        ) if ci_text else ""
        col.markdown(f"""
        <div style="background:#0f1623; border:1px solid #1e2a3d;
                    border-radius:14px; padding:20px 18px">
            <div style="font-size:0.7rem; text-transform:uppercase;
                        letter-spacing:1.5px; color:#4a6080; margin-bottom:8px">
                {label}
            </div>
            <div style="font-size:1.8rem; font-weight:700; color:{color}">
                {value}
            </div>
            <div style="font-size:0.8rem; color:#7a90a8; margin-top:4px">
                {subtext}
            </div>
            {ci_html}
        </div>
        """, unsafe_allow_html=True)

    hss_color = "#27ae60" if hss_all > 0.3 else "#d4a017" if hss_all > 0.1 else "#e74c3c"
    ci_lo, ci_hi = bootstrap_hss_ci(df['actual'].values, df['predicted'].values)
    metric_card(col1, "Heidke Skill Score (LOOCV)", f"{hss_all:.3f}",
                "WMO standard · >0.3 = skillful · see caveat below", hss_color,
                ci_text=f"95% bootstrap CI: [{ci_lo:.3f}, {ci_hi:.3f}] · n=1,092")
    metric_card(col2, "Overall Accuracy",   f"{accuracy:.1%}",
                "42 years · 13 regions · 1,092 forecasts")
    metric_card(col3, "Drought Detection",  f"{drought_hit:.1%}",
                f"of {len(drought_df)} drought cases correctly flagged",
                "#e74c3c" if drought_hit < 0.4 else "#d4a017")
    metric_card(col4, "Years Validated",    "42",
                "1981–2022 · leave-one-out method")

    st.write("")

    # ── HSS explainer ─────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:#0a0e18; border-left:3px solid #4a6080;
                border-radius:0 10px 10px 0; padding:14px 18px; margin:8px 0 24px 0;
                color:#8a9ab0; font-size:0.88rem; line-height:1.7">
        <b style="color:#c8d8e8">What is HSS?</b> The Heidke Skill Score measures how much
        better the model is than random chance. A score of 0 means no skill — equivalent
        to guessing. A score of 1 is perfect. WMO considers anything above 0.3 as skillful.
        <br><br>
        <b style="color:#d4a017">⚠️ Important: LOOCV vs prospective skill.</b>
        The scores shown above
        (Kiremt <b style="color:#c8d8e8">{hss_kiremt:.3f}</b> ·
        Belg <b style="color:#c8d8e8">{hss_belg:.3f}</b>)
        are from leave-one-year-out cross-validation (LOOCV). Because each held-out year
        is trained on <i>all other 41 years including future years</i>, LOOCV tends to
        overstate operational skill. Rolling-origin validation — training strictly on
        1981–T and forecasting T+1, advancing T from 1994 to 2021
        (27 test years × 13 regions = 351 pairs) — gives
        <b style="color:#c8d8e8">Kiremt HSS = +0.063</b> (Phase D) and
        <b style="color:#c8d8e8">Belg HSS = +0.071</b> (Phase F: region-specific AMM).
        A gap between LOOCV and rolling-origin is expected for small climate datasets.
        Rolling-origin is the <i>operational</i> skill metric — it is the primary basis
        for the per-region release tier (Full / Experimental / Suppressed) shown below.
        Both metrics are reported for full transparency.
    </div>
    """, unsafe_allow_html=True)

    # ── Two charts row ────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<p style="font-size:0.72rem; text-transform:uppercase; letter-spacing:2px; color:#4a6080; font-weight:600; margin-bottom:12px">Reliability Diagram — Drought Probability</p>', unsafe_allow_html=True)

        bins   = [0, 0.2, 0.3, 0.4, 0.5, 0.6, 1.0]
        labels = ['0–20%', '20–30%', '30–40%', '40–50%', '50–60%', '60%+']
        df['prob_bin'] = pd.cut(df['prob_below'], bins=bins, labels=labels)

        rel = df.groupby('prob_bin', observed=True).apply(
            lambda x: pd.Series({
                'actual_rate': (x['actual'] == 0).mean(),
                'mean_prob':   x['prob_below'].mean(),
                'count':       len(x),
            })
        ).reset_index()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[0, 1], y=[0, 1],
            mode='lines',
            line=dict(color='#4a6080', dash='dot', width=1),
            name='Perfect calibration',
            hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=rel['mean_prob'],
            y=rel['actual_rate'],
            mode='lines+markers',
            marker=dict(size=rel['count']/8, color='#e74c3c',
                        line=dict(color='#fff', width=1)),
            line=dict(color='#e74c3c', width=2),
            name='Azmera',
            hovertemplate='Forecast prob: %{x:.0%}<br>Actual drought rate: %{y:.0%}<extra></extra>'
        ))
        fig.update_layout(
            plot_bgcolor='#080c14', paper_bgcolor='#080c14',
            font=dict(color='#7a90a8', size=11), height=280,
            margin=dict(l=10, r=10, t=10, b=40), showlegend=True,
            legend=dict(font=dict(color='#7a90a8', size=10),
                        bgcolor='#0f1623', bordercolor='#1e2a3d'),
            xaxis=dict(title='Forecast drought probability',
                       gridcolor='#1a2030', tickformat='.0%', range=[0, 0.85]),
            yaxis=dict(title='Actual drought rate',
                       gridcolor='#1a2030', tickformat='.0%', range=[0, 0.85]),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Bubble size = number of forecasts in that bin. Rising line = meaningful probabilities.")

    with col2:
        st.markdown('<p style="font-size:0.72rem; text-transform:uppercase; letter-spacing:2px; color:#4a6080; font-weight:600; margin-bottom:12px">HSS by Region</p>', unsafe_allow_html=True)

        region_stats = []
        for region, grp in df.groupby('region'):
            if len(grp) < 10:
                continue
            h, _ = compute_hss(grp['actual'], grp['predicted'])
            region_stats.append({
                'region': REGION_DISPLAY.get(region, region),
                'hss':    h,
                'acc':    grp['correct'].mean(),
            })

        region_df = pd.DataFrame(region_stats).sort_values('hss', ascending=True)
        colors = ['#27ae60' if h > 0.3 else '#d4a017' if h > 0.1 else '#e74c3c'
                  for h in region_df['hss']]

        fig2 = go.Figure(go.Bar(
            x=region_df['hss'], y=region_df['region'],
            orientation='h', marker_color=colors,
            hovertemplate='%{y}<br>HSS: %{x:.3f}<extra></extra>'
        ))
        fig2.add_vline(x=0.3, line_color='#27ae60', line_dash='dot',
                       line_width=1, annotation_text='WMO threshold',
                       annotation_font_color='#27ae60', annotation_font_size=10)
        fig2.add_vline(x=0, line_color='#4a6080', line_width=1)
        fig2.update_layout(
            plot_bgcolor='#080c14', paper_bgcolor='#080c14',
            font=dict(color='#7a90a8', size=11), height=280,
            margin=dict(l=10, r=10, t=10, b=40),
            xaxis=dict(title='Heidke Skill Score', gridcolor='#1a2030'),
            yaxis=dict(gridcolor='#1a2030'),
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Green = skillful (HSS>0.3) · Yellow = marginal · Red = no skill")

    # ── Predicted vs actual timeline ──────────────────────────────
    st.markdown('<p style="font-size:0.72rem; text-transform:uppercase; letter-spacing:2px; color:#4a6080; font-weight:600; margin:20px 0 12px 0">Predicted vs Actual — All Regions Over Time</p>', unsafe_allow_html=True)

    season_filter = st.selectbox("Season", ["Kiremt", "Belg"], key="val_season")
    region_filter = st.selectbox("Region", ["All regions"] + sorted(REGION_DISPLAY.values()), key="val_region")

    plot_df = df[df['season'] == season_filter].copy()
    if region_filter != "All regions":
        rkey = {v: k for k, v in REGION_DISPLAY.items()}.get(region_filter, region_filter)
        plot_df = plot_df[plot_df['region'] == rkey]

    yearly = plot_df.groupby('year').agg(
        actual_mean=('actual', 'mean'),
        predicted_mean=('predicted', 'mean'),
        accuracy=('correct', 'mean'),
        prob_below=('prob_below', 'mean'),
    ).reset_index()

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=yearly['year'], y=yearly['actual_mean'],
        mode='lines+markers', name='Actual',
        line=dict(color='#c8d8e8', width=2), marker=dict(size=6),
        hovertemplate='%{x}<br>Actual: %{y:.2f}<extra></extra>'
    ))
    fig3.add_trace(go.Scatter(
        x=yearly['year'], y=yearly['predicted_mean'],
        mode='lines+markers', name='Predicted',
        line=dict(color='#e74c3c', width=2, dash='dash'), marker=dict(size=6),
        hovertemplate='%{x}<br>Predicted: %{y:.2f}<extra></extra>'
    ))
    for yr, desc in DROUGHT_YEARS.items():
        if yr in yearly['year'].values:
            fig3.add_vline(
                x=yr, line_color='#e74c3c', line_dash='dot', line_width=1,
                annotation_text=str(yr), annotation_font_color='#e74c3c',
                annotation_font_size=9,
            )
    fig3.update_layout(
        plot_bgcolor='#080c14', paper_bgcolor='#080c14',
        font=dict(color='#7a90a8', size=11), height=300,
        margin=dict(l=10, r=10, t=10, b=40),
        legend=dict(font=dict(color='#7a90a8'), bgcolor='#0f1623', bordercolor='#1e2a3d'),
        xaxis=dict(title='Year', gridcolor='#1a2030'),
        yaxis=dict(title='Mean category (0=Below, 1=Near, 2=Above)', gridcolor='#1a2030'),
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Red dashed vertical lines = known major drought years. 0=Below Normal, 1=Near Normal, 2=Above Normal.")

    # ── Key drought years scorecard ───────────────────────────────
    st.markdown('<p style="font-size:0.72rem; text-transform:uppercase; letter-spacing:2px; color:#4a6080; font-weight:600; margin:20px 0 12px 0">Key Drought Year Scorecard</p>', unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#0a0e18; border-left:3px solid #4a6080;
                border-radius:0 10px 10px 0; padding:12px 16px; margin-bottom:16px;
                color:#8a9ab0; font-size:0.82rem; line-height:1.7">
        <b style="color:#c8d8e8">Why some drought years are harder to detect:</b>
        Droughts driven by strong El Niño or La Niña signals (2002, 2009) are detectable
        from ocean conditions months ahead — all statistical systems perform reasonably well
        on these. Neutral-year droughts (1984, 1994, 2003) are caused by local atmospheric
        patterns with no large-scale ocean precursor — these are missed by <i>all</i>
        statistical seasonal forecast systems globally, including ICPAC and ECMWF.
        The 2015 El Niño produced highly uneven impacts across regions, reducing region-level
        detection even though the El Niño signal was the strongest on record.
    </div>
    """, unsafe_allow_html=True)

    rows = []
    for yr, desc in DROUGHT_YEARS.items():
        yr_df = df[(df['year'] == yr) & (df['actual'] == 0)]
        if len(yr_df) == 0:
            continue
        hit_rate      = yr_df['correct'].mean()
        mean_prob     = yr_df['prob_below'].mean()
        regions_hit   = yr_df['correct'].sum()
        total_regions = len(yr_df)
        rows.append({
            'Year':             yr,
            'Event':            desc,
            'Drought Regions':  total_regions,
            'Correctly Flagged':f"{int(regions_hit)}/{total_regions}",
            'Detection Rate':   hit_rate,
            'Mean Drought Prob':mean_prob,
        })

    scorecard = pd.DataFrame(rows)

    for _, row in scorecard.iterrows():
        rate  = row['Detection Rate']
        prob  = row['Mean Drought Prob']
        color = '#27ae60' if rate >= 0.5 else '#d4a017' if rate >= 0.3 else '#e74c3c'
        icon  = '✅' if rate >= 0.5 else '🟠' if rate >= 0.3 else '⚠️'

        st.markdown(f"""
        <div style="background:#0f1623; border:1px solid #1e2a3d; border-left:3px solid {color};
                    border-radius:0 12px 12px 0; padding:14px 18px; margin-bottom:8px;
                    display:flex; justify-content:space-between; align-items:center">
            <div>
                <span style="color:#c8d8e8; font-weight:600">{icon} {row['Year']}</span>
                <span style="color:#4a6080; font-size:0.85rem; margin-left:12px">{row['Event']}</span>
            </div>
            <div style="text-align:right">
                <span style="color:{color}; font-weight:600">{rate:.0%} detected</span>
                <span style="color:#4a6080; font-size:0.82rem; margin-left:12px">
                    {row['Correctly Flagged']} regions · avg drought prob {prob:.0%}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Methodology note ──────────────────────────────────────────
    st.markdown("""
    <div style="background:#0a0e18; border-left:3px solid #4a6080;
                border-radius:0 10px 10px 0; padding:16px 20px; margin-top:24px;
                color:#8a9ab0; font-size:0.85rem; line-height:1.8">
        <b style="color:#c8d8e8">Methodology</b><br>
        Primary validation uses leave-one-out cross-validation (LOOCV) across 42 years (1981–2022),
        13 Ethiopian regions, and 2 seasons — 1,092 total forecast-verification pairs.
        Model: <b style="color:#c8d8e8">Logistic Regression (L2 regularised, C=0.5, balanced class weights)</b> —
        selected after LOOCV comparison against XGBoost, Random Forest, and an Analog method.
        LR achieved the highest overall LOOCV HSS, consistent with
        climate forecasting literature recommending simpler regularised models for small datasets
        (Wilks 2006, Weigel et al. 2008).
        Features: ENSO, IOD, PDO and Atlantic SST at 1–3 month lags.
        Skill metric: Heidke Skill Score (HSS), standard WMO/ICPAC verification metric.
        Neutral-year droughts (1984, 1994, 2003) are known to be difficult for all
        statistical seasonal forecast systems due to weak large-scale climate forcing.
        OND and Bega seasons are not included — validation showed insufficient skill
        (HSS &lt; 0) for those seasons and are served as satellite monitoring only.
        <br><br>
        <b style="color:#d4a017">⚠️ Rolling-origin validation (prospective skill):</b>
        In addition to LOOCV, rolling-origin validation was conducted: training on 1981–T and
        forecasting year T+1, advancing T from 1994 to 2021 (27 seasons × 13 regions = 351 pairs).
        Rolling-origin results: <b style="color:#c8d8e8">Kiremt HSS = +0.063</b> (Phase D) and
        <b style="color:#c8d8e8">Belg HSS = +0.071</b> (Phase F: region-specific AMM Jan index).
        Phase F improved Belg rolling-origin from +0.015 (Phase D) to +0.071 by adding the
        Atlantic Meridional Mode January index for 7 of 13 Belg regions where it demonstrably
        raised prospective skill. Rolling-origin is the operationally relevant measure of
        forecast skill on unseen seasons; LOOCV provides an optimistic upper bound. Both reported.
        <br><br>
        <b style="color:#2ecc71">✅ Train/inference consistency (resolved Phase C):</b>
        <code>spi_lag3</code> (previous-season SPI) has been removed from all per-region models.
        Kiremt models use <code>belg_antecedent_anom_z</code> — a CHIRPS Belg z-score computed
        consistently at training and inference time from the same CHIRPS baseline (Phase D).
        Belg models use <code>amm_sst_jan</code> (January AMM SST) for 7 BELG_AMM_INCLUDE regions
        and lean SST features only for the remaining 6 regions (Phase F).
    </div>
    """, unsafe_allow_html=True)

    # ── Known limitations ─────────────────────────────────────────
    st.write("")
    with st.expander("⚠️ Known Limitations — Read Before Using for Decision-Making"):

        LIMITATIONS = [
            {
                "title": "Neutral-year droughts cannot be predicted",
                "severity": "fundamental",
                "detail": (
                    "Droughts caused by local atmospheric patterns — not driven by El Niño, La Niña, "
                    "or IOD — have no detectable large-scale ocean precursor. This means they are "
                    "unpredictable by any statistical or dynamical seasonal forecast system, including "
                    "ICPAC and ECMWF. The 1984 famine, 1994 drought, and 2003 drought all fall in this "
                    "category. Azmera cannot warn of these events in advance."
                ),
                "status": "Shared limitation across all operational forecast systems globally.",
            },
            {
                "title": "Regional heterogeneity during ENSO events",
                "severity": "significant",
                "detail": (
                    "The same El Niño or La Niña signal can produce drought in one Ethiopian region "
                    "and above-normal rains in another simultaneously. Azmera produces one forecast "
                    "per region using a single centroid coordinate — it cannot capture the intra-region "
                    "variability that makes some zones drought-affected while neighbouring zones are not. "
                    "The 2015 El Niño is the clearest example: Afar and parts of Oromia experienced "
                    "severe drought while Somali region received above-normal rainfall."
                ),
                "status": "Partially addressed by zone-level models. Full spatial resolution requires gridded data pipeline (in development).",
            },
            {
                "title": "Training dataset is borderline in size",
                "severity": "significant",
                "detail": (
                    "The model is trained on 42 years of data (1981–2022) across 13 regions, "
                    "giving approximately 546 samples per season for a 3-class classification problem. "
                    "Climate forecasting literature recommends simpler regularised models for datasets "
                    "of this size — which is why Logistic Regression outperformed XGBoost and Random Forest "
                    "in our LOOCV comparison. The class imbalance (drought years are rarer than normal years) "
                    "is mitigated by balanced class weighting but cannot fully substitute for more training data."
                ),
                "status": "Mitigated by balanced class weights, L2 regularisation, and LOOCV model selection. Longer records (pre-1981 GPCC data) under evaluation.",
            },
            {
                "title": "OND and Bega seasons have no validated forecast",
                "severity": "significant",
                "detail": (
                    "The October–December (OND) short rains and January–February (Bega) dry-season "
                    "rains are served as satellite monitoring only. During development, 4-season models "
                    "were trained for these seasons but produced negative HSS scores and showed no "
                    "meaningful probability calibration — forecasting these seasons was worse than "
                    "climatological chance. Showing these forecasts would actively mislead users. "
                    "OND affects southern and eastern Ethiopia including Somali and SNNPR regions — "
                    "these populations currently receive monitoring data only, not predictive guidance."
                ),
                "status": "Under development. Requires gridded spatial data and extended training records to improve skill.",
            },
            {
                "title": "Belg season skill is region-variable and generally low",
                "severity": "significant",
                "detail": (
                    "The Belg (March–May) short rains remain challenging to forecast. Rolling-origin "
                    "validation (Phase F, 27 test years × 13 regions) gives an aggregate HSS of +0.071 — "
                    "positive but well below the WMO skillful threshold of 0.3. Per-region skill varies "
                    "substantially: Amhara (+0.199) and South West (+0.160) demonstrate meaningful skill; "
                    "Oromia (−0.084), SNNPR (−0.101), and Sidama (−0.025) show negative rolling-origin HSS "
                    "and are suppressed (no forecast issued). The Atlantic Meridional Mode Jan index "
                    "(amm_sst_jan, Phase F) improved 7-region Belg rolling-origin from +0.015 to +0.071. "
                    "Belg rainfall is driven by Atlantic SST and ITCZ position — weaker teleconnections "
                    "than Kiremt. This is a known challenge across all statistical Belg forecast systems."
                ),
                "status": (
                    "Improved from +0.015 to +0.071 rolling-origin via Phase F AMM feature (region-specific). "
                    "3 Belg regions suppressed. Further improvement may require ITCZ position indices or "
                    "ensemble methods. Phase G evaluation planned."
                ),
            },
            {
                "title": "Model uses static lagged indices, not real-time updates",
                "severity": "moderate",
                "detail": (
                    "Forecasts are generated using the 3 most recent monthly values of ENSO, IOD, PDO, "
                    "and Atlantic SST — typically 1–3 months before the target season. The model does "
                    "not update as the season progresses. If ocean conditions change rapidly after the "
                    "forecast is generated (e.g. an El Niño developing or collapsing mid-season), "
                    "the forecast will not reflect this. Users should re-run forecasts monthly as "
                    "new climate index data becomes available."
                ),
                "status": "By design for the current version. Real-time re-forecasting is on the roadmap.",
            },
            {
                "title": "Logistic Regression may underestimate tail risks under unprecedented climate states",
                "severity": "moderate",
                "detail": (
                    "The current model is Logistic Regression (L2 regularised, C=0.5) — chosen because "
                    "climate forecasting literature recommends simpler regularised models for small datasets, "
                    "and it outperformed XGBoost and Random Forest in our LOOCV comparison. "
                    "LR extrapolates linearly beyond the training distribution, which is more stable than "
                    "tree-based models under mild climate shift. However it may underestimate drought "
                    "probability under truly unprecedented ocean states (e.g. ENSO indices far outside "
                    "the 1981–2022 historical range) as the linear decision boundary cannot capture "
                    "highly non-linear climate regime shifts."
                ),
                "status": "LR is the most robust choice for this dataset size. Ensemble methods combining LR with analog approaches are under evaluation for v2.",
            },
            {
                "title": "Advisory text is AI-generated and unverified",
                "severity": "moderate",
                "detail": (
                    "The farmer advisory displayed after each forecast is generated by a large language "
                    "model (GPT-4o) prompted with the forecast probabilities and regional context. "
                    "It has not been reviewed by agronomists or validated against local farming calendars "
                    "for every region. Crop recommendations may not reflect local varieties, market "
                    "access constraints, or specific agroecological conditions. Advisories should be "
                    "treated as a starting point, not prescriptive guidance."
                ),
                "status": "Expert agronomist review of advisory templates planned for v2.",
            },
        ]

        severity_colors = {
            "fundamental": "#e74c3c",
            "significant": "#d4a017",
            "moderate":    "#4a6080",
        }
        severity_labels = {
            "fundamental": "Fundamental — cannot be solved by improving the model",
            "significant": "Significant — actively being worked on",
            "moderate":    "Moderate — known and manageable",
        }

        for lim in LIMITATIONS:
            color = severity_colors[lim["severity"]]
            label = severity_labels[lim["severity"]]
            st.markdown(f"""
            <div style="background:#0f1623; border:1px solid #1e2a3d;
                        border-left:4px solid {color};
                        border-radius:0 12px 12px 0; padding:16px 20px; margin-bottom:10px">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;
                            margin-bottom:8px">
                    <span style="color:#c8d8e8; font-weight:600; font-size:0.95rem">
                        {lim['title']}
                    </span>
                    <span style="color:{color}; font-size:0.7rem; font-weight:600;
                                 text-transform:uppercase; letter-spacing:1px;
                                 white-space:nowrap; margin-left:12px">
                        {lim['severity']}
                    </span>
                </div>
                <div style="color:#8a9ab0; font-size:0.85rem; line-height:1.7; margin-bottom:10px">
                    {lim['detail']}
                </div>
                <div style="color:{color}; font-size:0.78rem; font-style:italic; line-height:1.5">
                    📌 {lim['status']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Release matrix ────────────────────────────────────────────
    st.write("")
    st.markdown(
        '<p style="font-size:0.72rem; text-transform:uppercase; letter-spacing:2px; '
        'color:#4a6080; font-weight:600; margin:24px 0 12px 0">'
        'Release Matrix — Per-Region Forecast Status</p>',
        unsafe_allow_html=True,
    )
    st.markdown("""
    <div style="background:#0a0e18; border-left:3px solid #4a6080;
                border-radius:0 10px 10px 0; padding:12px 16px; margin-bottom:16px;
                color:#8a9ab0; font-size:0.82rem; line-height:1.7">
        <b style="color:#c8d8e8">Basis:</b> rolling-origin validation (train 1981–T,
        forecast T+1, T: 1994–2021 · 27 test years × 13 regions = 351 pairs per season).
        Kiremt = Phase D features · Belg = Phase F features (region-specific AMM Jan).
        Thresholds: <b style="color:#27ae60">Full</b> = rolling-origin HSS ≥ 0.10 ·
        <b style="color:#d4a017">Experimental</b> = HSS in (0.0, 0.10) ·
        <b style="color:#e74c3c">Suppressed</b> = HSS ≤ 0.0.
        Suppressed regions show "No Validated Forecast" instead of a verdict card.
    </div>
    """, unsafe_allow_html=True)

    # Release matrix data: (region_display, kiremt_ro_hss, belg_ro_hss)
    RELEASE_MATRIX = [
        ("Addis Ababa",       -0.049,  +0.111),
        ("Afar",              +0.071,  +0.046),
        ("Amhara",            +0.044,  +0.199),
        ("Benishangul-Gumz",  +0.471,  +0.056),
        ("Dire Dawa",         +0.024,  +0.096),
        ("Gambela",           +0.012,  +0.147),
        ("Harari",            +0.102,  +0.096),
        ("Oromia",            -0.111,  -0.084),
        ("Sidama",            -0.130,  -0.025),
        ("SNNPR",             +0.077,  -0.101),
        ("Somali",            +0.206,  +0.100),
        ("South West",        +0.025,  +0.160),
        ("Tigray",            +0.106,  +0.032),
    ]

    def _tier(hss):
        if hss >= 0.10:  return ("✅ Full",         "#27ae60")
        if hss > 0.00:   return ("⚠️ Experimental", "#d4a017")
        return                   ("❌ Suppressed",   "#e74c3c")

    # Header
    st.markdown("""
    <div style="display:grid; grid-template-columns:1.8fr 1fr 1.2fr 1fr 1.2fr;
                gap:4px; padding:8px 12px; font-size:0.7rem; font-weight:600;
                text-transform:uppercase; letter-spacing:1px; color:#4a6080;
                background:#0a0e18; border-radius:8px 8px 0 0; margin-top:4px">
        <span>Region</span>
        <span style="text-align:right">Kiremt RO-HSS</span>
        <span style="text-align:center">Kiremt Tier</span>
        <span style="text-align:right">Belg RO-HSS</span>
        <span style="text-align:center">Belg Tier</span>
    </div>
    """, unsafe_allow_html=True)

    for region_name, k_hss, b_hss in RELEASE_MATRIX:
        k_label, k_color = _tier(k_hss)
        b_label, b_color = _tier(b_hss)
        st.markdown(f"""
        <div style="display:grid; grid-template-columns:1.8fr 1fr 1.2fr 1fr 1.2fr;
                    gap:4px; padding:8px 12px; font-size:0.82rem; color:#c8d8e8;
                    background:#0f1623; border-bottom:1px solid #1e2a3d;
                    align-items:center">
            <span style="font-weight:600">{region_name}</span>
            <span style="text-align:right; font-family:monospace;
                         color:{k_color}">{k_hss:+.3f}</span>
            <span style="text-align:center; font-size:0.78rem;
                         color:{k_color}">{k_label}</span>
            <span style="text-align:right; font-family:monospace;
                         color:{b_color}">{b_hss:+.3f}</span>
            <span style="text-align:center; font-size:0.78rem;
                         color:{b_color}">{b_label}</span>
        </div>
        """, unsafe_allow_html=True)

    # Aggregate row
    k_agg = +0.063
    b_agg = +0.071
    k_agg_color = "#d4a017"   # experimental range
    b_agg_color = "#d4a017"
    st.markdown(f"""
    <div style="display:grid; grid-template-columns:1.8fr 1fr 1.2fr 1fr 1.2fr;
                gap:4px; padding:8px 12px; font-size:0.82rem;
                background:#0a0e18; border-radius:0 0 8px 8px;
                align-items:center; border-top:2px solid #1e2a3d">
        <span style="color:#7a90a8; font-weight:600; font-size:0.78rem">
            AGGREGATE (351 pairs)
        </span>
        <span style="text-align:right; font-family:monospace;
                     font-weight:700; color:{k_agg_color}">{k_agg:+.3f}</span>
        <span style="text-align:center; font-size:0.72rem;
                     color:{k_agg_color}">Phase D</span>
        <span style="text-align:right; font-family:monospace;
                     font-weight:700; color:{b_agg_color}">{b_agg:+.3f}</span>
        <span style="text-align:center; font-size:0.72rem;
                     color:{b_agg_color}">Phase F</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:12px; color:#4a6080; font-size:0.78rem; line-height:1.6">
        <b style="color:#c8d8e8">Why this matters:</b>
        Oromia and Addis Ababa Kiremt show positive LOOCV scores (+0.227 and +0.039) but
        negative rolling-origin HSS (−0.111 and −0.049) — a classic sign of LOOCV
        overfitting when future years appear in training. Rolling-origin is the honest test.
        Gambela Kiremt shows the opposite: LOOCV −0.013 but rolling-origin +0.012 —
        the leave-one-out test understates its prospective skill.
        Harari uses the Dire Dawa model (pixel-identical CHIRPS extraction confirmed).
    </div>
    """, unsafe_allow_html=True)