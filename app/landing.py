"""
Azmera — Landing Page
"""

import streamlit as st
import os

st.set_page_config(
    page_title="Azmera — Ethiopia Rainfall Forecast",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700;900&family=Sora:wght@300;400;500;600&family=Noto+Sans+Ethiopic:wght@400;600&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, .stApp { background-color: #05080f; color: #e0e8f0; }
.block-container { padding: 0 !important; max-width: 100% !important; }
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.hero { min-height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 80px 40px; position: relative; overflow: hidden; background: radial-gradient(ellipse 80% 60% at 50% 0%, rgba(16,80,40,0.35) 0%, transparent 70%), radial-gradient(ellipse 60% 40% at 20% 80%, rgba(10,40,80,0.3) 0%, transparent 60%), #05080f; }
.hero::before { content: ''; position: absolute; inset: 0; background-image: radial-gradient(circle at 1px 1px, rgba(255,255,255,0.04) 1px, transparent 0); background-size: 40px 40px; pointer-events: none; }
.hero-eyebrow { font-family: 'Sora', sans-serif; font-size: 0.72rem; font-weight: 600; letter-spacing: 4px; text-transform: uppercase; color: #4a9060; margin-bottom: 24px; animation: fadeUp 0.8s ease both; }
.hero-title { font-family: 'Playfair Display', serif; font-size: clamp(3rem, 8vw, 7rem); font-weight: 900; line-height: 1.0; letter-spacing: -2px; color: #f0f8f0; margin-bottom: 12px; animation: fadeUp 0.8s ease 0.1s both; }
.hero-title-amharic { font-family: 'Noto Sans Ethiopic', sans-serif; font-size: clamp(1.5rem, 4vw, 3rem); font-weight: 400; color: #4a9060; margin-bottom: 32px; animation: fadeUp 0.8s ease 0.2s both; }
.hero-subtitle { font-family: 'Sora', sans-serif; font-size: clamp(1rem, 2vw, 1.25rem); font-weight: 300; color: #8aacb0; max-width: 640px; line-height: 1.8; margin-bottom: 48px; animation: fadeUp 0.8s ease 0.3s both; }
.hero-cta-group { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; animation: fadeUp 0.8s ease 0.4s both; }
.cta-primary { background: linear-gradient(135deg, #1a6b40, #27ae60); color: white; font-family: 'Sora', sans-serif; font-size: 1rem; font-weight: 600; padding: 16px 40px; border-radius: 100px; text-decoration: none; letter-spacing: 0.5px; box-shadow: 0 8px 32px rgba(39,174,96,0.3); transition: all 0.3s ease; display: inline-block; }
.cta-primary:hover { transform: translateY(-2px); box-shadow: 0 12px 40px rgba(39,174,96,0.5); color: white; text-decoration: none; }
.cta-secondary { background: transparent; color: #8aacb0; font-family: 'Sora', sans-serif; font-size: 1rem; font-weight: 400; padding: 16px 32px; border-radius: 100px; border: 1px solid #1e3040; text-decoration: none; transition: all 0.3s ease; display: inline-block; }
.cta-secondary:hover { border-color: #4a9060; color: #4a9060; text-decoration: none; }
.stats-strip { display: flex; justify-content: center; gap: 0; margin-top: 80px; animation: fadeUp 0.8s ease 0.5s both; border-top: 1px solid #0f1820; border-bottom: 1px solid #0f1820; width: 100%; max-width: 900px; }
.stat-item { flex: 1; padding: 24px 32px; text-align: center; border-right: 1px solid #0f1820; }
.stat-item:last-child { border-right: none; }
.stat-number { font-family: 'Playfair Display', serif; font-size: 2rem; font-weight: 700; color: #4a9060; display: block; }
.stat-label { font-family: 'Sora', sans-serif; font-size: 0.75rem; color: #4a6070; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 4px; display: block; }
.story-section { padding: 120px 40px; max-width: 1100px; margin: 0 auto; }
.section-tag { font-family: 'Sora', sans-serif; font-size: 0.72rem; font-weight: 600; letter-spacing: 4px; text-transform: uppercase; color: #4a9060; margin-bottom: 20px; display: block; }
.story-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 80px; align-items: center; }
.story-headline { font-family: 'Playfair Display', serif; font-size: clamp(2rem, 4vw, 3rem); font-weight: 700; color: #f0f8f0; line-height: 1.2; letter-spacing: -0.5px; margin-bottom: 24px; }
.story-body { font-family: 'Sora', sans-serif; font-size: 1rem; color: #7a9aaa; line-height: 1.9; margin-bottom: 20px; }
.story-body strong { color: #c8e0d8; }
.story-quote { border-left: 3px solid #4a9060; padding: 20px 24px; background: rgba(26, 107, 64, 0.08); border-radius: 0 12px 12px 0; margin: 32px 0; font-family: 'Playfair Display', serif; font-size: 1.15rem; color: #c8e0d8; line-height: 1.7; font-style: italic; }
.how-section { padding: 100px 40px; background: linear-gradient(180deg, #05080f 0%, #070d18 50%, #05080f 100%); }
.how-inner { max-width: 1100px; margin: 0 auto; }
.how-title { font-family: 'Playfair Display', serif; font-size: clamp(2rem, 4vw, 2.8rem); font-weight: 700; color: #f0f8f0; text-align: center; margin-bottom: 64px; letter-spacing: -0.5px; }
.steps-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px; }
.step-card { background: #080e1a; border: 1px solid #0f1e2e; border-radius: 20px; padding: 36px 32px; position: relative; transition: border-color 0.3s ease; }
.step-card:hover { border-color: #1a5030; }
.step-number { font-family: 'Playfair Display', serif; font-size: 3rem; font-weight: 900; color: #0f2018; position: absolute; bottom: 20px; right: 24px; line-height: 1; }
.step-title { font-family: 'Sora', sans-serif; font-size: 1.05rem; font-weight: 600; color: #c8e0d8; margin-bottom: 10px; }
.step-desc { font-family: 'Sora', sans-serif; font-size: 0.88rem; color: #4a7080; line-height: 1.7; }
.validation-section { padding: 100px 40px; max-width: 1100px; margin: 0 auto; }
.validation-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 48px; align-items: start; }
.val-card { background: #080e1a; border: 1px solid #0f1e2e; border-radius: 20px; padding: 40px; }
.val-headline { font-family: 'Playfair Display', serif; font-size: 1.8rem; font-weight: 700; color: #4a9060; margin-bottom: 8px; }
.val-subline { font-family: 'Sora', sans-serif; font-size: 0.85rem; color: #4a7080; margin-bottom: 20px; }
.val-detail { font-family: 'Sora', sans-serif; font-size: 0.92rem; color: #7a9aaa; line-height: 1.7; }
.drought-years { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
.drought-badge { background: rgba(192, 57, 43, 0.15); border: 1px solid rgba(192, 57, 43, 0.3); color: #e74c3c; font-family: 'Sora', sans-serif; font-size: 0.78rem; font-weight: 600; padding: 4px 12px; border-radius: 100px; }
.correct-badge { background: rgba(39, 174, 96, 0.15); border: 1px solid rgba(39, 174, 96, 0.3); color: #27ae60; font-family: 'Sora', sans-serif; font-size: 0.78rem; font-weight: 600; padding: 4px 12px; border-radius: 100px; }
.audience-section { padding: 100px 40px; background: #070d18; }
.audience-inner { max-width: 1100px; margin: 0 auto; }
.audience-title { font-family: 'Playfair Display', serif; font-size: clamp(2rem, 4vw, 2.8rem); font-weight: 700; color: #f0f8f0; text-align: center; margin-bottom: 56px; }
.audience-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; }
.audience-card { background: #05080f; border: 1px solid #0f1e2e; border-radius: 20px; padding: 36px; transition: border-color 0.3s ease; }
.audience-card:hover { border-color: #1a5030; }
.audience-role { font-family: 'Sora', sans-serif; font-size: 0.72rem; font-weight: 600; letter-spacing: 3px; text-transform: uppercase; color: #4a9060; margin-bottom: 8px; }
.audience-title-sm { font-family: 'Playfair Display', serif; font-size: 1.3rem; font-weight: 700; color: #c8e0d8; margin-bottom: 12px; }
.audience-desc { font-family: 'Sora', sans-serif; font-size: 0.88rem; color: #4a7080; line-height: 1.7; }
.final-cta { padding: 140px 40px; text-align: center; position: relative; overflow: hidden; background: radial-gradient(ellipse 70% 50% at 50% 50%, rgba(16,80,40,0.2) 0%, transparent 70%), #05080f; }
.final-title { font-family: 'Playfair Display', serif; font-size: clamp(2.5rem, 5vw, 4.5rem); font-weight: 900; color: #f0f8f0; letter-spacing: -1px; margin-bottom: 20px; line-height: 1.1; }
.final-sub { font-family: 'Sora', sans-serif; font-size: 1.1rem; color: #7a9aaa; max-width: 520px; margin: 0 auto 48px auto; line-height: 1.7; text-align: center; }
.data-sources { display: flex; justify-content: center; gap: 24px; flex-wrap: wrap; margin-top: 64px; }
.source-pill { background: #080e1a; border: 1px solid #0f1e2e; border-radius: 100px; padding: 8px 20px; font-family: 'Sora', sans-serif; font-size: 0.75rem; color: #4a7080; letter-spacing: 0.5px; }
@keyframes fadeUp { from { opacity: 0; transform: translateY(24px); } to { opacity: 1; transform: translateY(0); } }
@media (max-width: 768px) { .story-grid, .steps-grid, .validation-grid, .audience-grid { grid-template-columns: 1fr; gap: 32px; } .stats-strip { flex-direction: column; } .stat-item { border-right: none; border-bottom: 1px solid #0f1820; } }
</style>
""", unsafe_allow_html=True)


# ── Hero ──────────────────────────────────────────────────────────
st.markdown("""
<section class="hero">
<span class="hero-eyebrow">Introducing Azmera</span>
<h1 class="hero-title">Know Before<br>the Rains Fail</h1>
<p class="hero-title-amharic">አዝመራ — Harvest Season</p>
<p class="hero-subtitle">Seasonal rainfall forecasting for Ethiopian farmers, humanitarian organizations, and policymakers — up to 3 months before the growing season begins.</p>
<div class="hero-cta-group">
<a href="https://azmera-forecast.streamlit.app" target="_blank" class="cta-primary">Try Azmera Now</a>
<a href="#story" class="cta-secondary">Read the Story</a>
</div>
<div class="stats-strip">
<div class="stat-item"><span class="stat-number">44</span><span class="stat-label">Years of Data</span></div>
<div class="stat-item"><span class="stat-number">78</span><span class="stat-label">Zones Covered</span></div>
<div class="stat-item"><span class="stat-number">156</span><span class="stat-label">Forecast Models</span></div>
<div class="stat-item"><span class="stat-number">+0.063</span><span class="stat-label">Kiremt Prospective HSS</span></div>
<div class="stat-item"><span class="stat-number">5</span><span class="stat-label">Ocean Signals</span></div>
</div>
</section>
""", unsafe_allow_html=True)


# ── Story ─────────────────────────────────────────────────────────
st.markdown("""
<section class="story-section" id="story">
<div class="story-grid">
<div>
<span class="section-tag">Why Azmera Exists</span>
<h2 class="story-headline">The 1997 drought changed Ethiopia. We're making sure the next one doesn't catch anyone off guard.</h2>
</div>
<div>
<p class="story-body">In 1997, a powerful El Niño triggered one of Ethiopia's most devastating droughts. Crops failed. Livestock died. Millions faced food insecurity across the Horn of Africa. It is the drought that <strong>most Ethiopians alive today remember</strong> — not because it was the worst in history, but because it struck without adequate warning reaching the farmers who needed it most.</p>
<p class="story-body">Ethiopia has world-class climate scientists at ICPAC and the National Meteorological Institute. But their forecasts are written for policymakers — not for a farmer in Oromia deciding whether to plant Teff or Sorghum next month.</p>
<div class="story-quote">"The science exists. The data exists. What's missing is the last mile — turning climate forecasts into decisions farmers can actually act on."</div>
<p class="story-body">Azmera bridges that gap. Built by an Ethiopian engineer using NASA satellite data, NOAA ocean indices, and 44 years of rainfall records — translated into plain language, <strong>in Amharic</strong>, for the people who need it most.</p>
</div>
</div>
</section>
""", unsafe_allow_html=True)


# ── How It Works ──────────────────────────────────────────────────
st.markdown("""
<section class="how-section">
<div class="how-inner">
<h2 class="how-title">How Azmera Works</h2>
<div class="steps-grid">
<div class="step-card">
<span class="step-number">1</span>
<div class="step-title">Read the Ocean Signals</div>
<p class="step-desc">Azmera monitors 4 global climate indices — El Niño / La Niña (ENSO), the Indian Ocean Dipole (IOD), the Pacific Decadal Oscillation (PDO), and Atlantic sea surface temperatures. These ocean patterns drive Ethiopian rainfall months before the season begins.</p>
</div>
<div class="step-card">
<span class="step-number">2</span>
<div class="step-title">Run 156 Zone-Level Models</div>
<p class="step-desc">156 statistical models — one per zone per season — trained on 44 years of CHIRPS 5km satellite rainfall data predict whether Kiremt or Belg will be below, near, or above normal. Each zone is calibrated independently to its own local rainfall patterns.</p>
</div>
<div class="step-card">
<span class="step-number">3</span>
<div class="step-title">Deliver Actionable Guidance</div>
<p class="step-desc">Farmers receive plain-language crop recommendations — which Ethiopian crops to plant, when to plant them, how to prepare water storage — in both English and Amharic. Paired with observed CHIRPS rainfall (season-to-date vs 1991–2020 baseline) and live WFP market prices for Teff, Maize, Sorghum, Wheat, and Barley.</p>
</div>
</div>
</div>
</section>
""", unsafe_allow_html=True)


# ── Zone Drill-Down Section ───────────────────────────────────────
st.markdown("""
<section style="padding: 100px 40px; max-width: 1100px; margin: 0 auto;">
<span class="section-tag" style="display:block; text-align:center; margin-bottom:16px">Zone-Level Forecasting</span>
<h2 style="font-family: 'Playfair Display', serif; font-size: clamp(2rem, 4vw, 2.8rem); font-weight: 700; color: #f0f8f0; text-align: center; margin-bottom: 16px; letter-spacing: -0.5px;">Beyond the Region.<br>Zone-Level Forecasts Closer to Your Farm.</h2>
<p style="font-family: 'Sora', sans-serif; font-size: 1rem; color: #7a9aaa; text-align: center; max-width: 640px; margin: 0 auto 64px auto; line-height: 1.8;">Ethiopia is vast. A drought in West Oromia looks nothing like conditions in Bale. Azmera forecasts at the <strong style="color:#c8e0d8">zone level</strong> — 78 zones across all regions — so communities get forecasts specific to where they actually farm.</p>
<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px; margin-bottom: 48px;">
<div style="background: #080e1a; border: 1px solid #0f1e2e; border-radius: 20px; padding: 36px; text-align:center;">
<span style="font-family: 'Playfair Display', serif; font-size: 2.5rem; font-weight: 900; color: #4a9060; display:block; margin-bottom:8px;">78</span>
<span style="font-family: 'Sora', sans-serif; font-size: 0.85rem; color: #4a7080; text-transform:uppercase; letter-spacing:2px;">Zones Modeled</span>
<p style="font-family: 'Sora', sans-serif; font-size: 0.85rem; color: #4a7080; line-height:1.7; margin-top:12px;">Separate models trained for each zone and season combination using CHIRPS 5km satellite rainfall data going back to 1981.</p>
</div>
<div style="background: #080e1a; border: 1px solid #0f1e2e; border-radius: 20px; padding: 36px; text-align:center;">
<span style="font-family: 'Playfair Display', serif; font-size: 2.5rem; font-weight: 900; color: #4a9060; display:block; margin-bottom:8px;">156</span>
<span style="font-family: 'Sora', sans-serif; font-size: 0.85rem; color: #4a7080; text-transform:uppercase; letter-spacing:2px;">Forecast Models</span>
<p style="font-family: 'Sora', sans-serif; font-size: 0.85rem; color: #4a7080; line-height:1.7; margin-top:12px;">78 zones × 2 seasons (Kiremt + Belg) — each trained and validated independently against decades of observed rainfall.</p>
</div>
<div style="background: #080e1a; border: 1px solid #0f1e2e; border-radius: 20px; padding: 36px; text-align:center;">
<span style="font-family: 'Playfair Display', serif; font-size: 2.5rem; font-weight: 900; color: #4a9060; display:block; margin-bottom:8px;">Map</span>
<span style="font-family: 'Sora', sans-serif; font-size: 0.85rem; color: #4a7080; text-transform:uppercase; letter-spacing:2px;">Interactive</span>
<p style="font-family: 'Sora', sans-serif; font-size: 0.85rem; color: #4a7080; line-height:1.7; margin-top:12px;">Click any region on the risk map to drill into its zones — each colored by its own forecast. One click, instant zone-level outlook.</p>
</div>
</div>
<div style="background: linear-gradient(135deg, rgba(26,107,64,0.1), rgba(10,40,80,0.15)); border: 1px solid #1a5030; border-radius: 20px; padding: 40px; display:flex; gap:40px; align-items:center; flex-wrap:wrap;">
<div style="flex:1; min-width:280px;">
<div style="font-family: 'Sora', sans-serif; font-size: 0.72rem; font-weight: 600; letter-spacing: 3px; text-transform: uppercase; color: #4a9060; margin-bottom: 12px;">How the Map Works</div>
<h3 style="font-family: 'Playfair Display', serif; font-size: 1.5rem; font-weight: 700; color: #c8e0d8; margin-bottom: 16px;">Select a region — see every zone colored by its forecast</h3>
<p style="font-family: 'Sora', sans-serif; font-size: 0.92rem; color: #7a9aaa; line-height: 1.8;">The Risk Map shows all of Ethiopia colored by seasonal outlook. Select a region in the sidebar or click it on the map — the view drills into every zone within that region, each colored by its own independent forecast. Click any zone card to generate a full advisory.</p>
</div>
<div style="flex:0 0 auto; display:flex; flex-direction:column; gap:12px;">
<div style="background:#0f1820; border-radius:12px; padding:16px 24px; border-left: 3px solid #4caf84;">
<div style="font-family:'Sora',sans-serif; font-size:0.72rem; color:#4a7080; text-transform:uppercase; letter-spacing:2px; margin-bottom:4px;">Above Normal</div>
<div style="font-family:'Playfair Display',serif; font-size:1.1rem; color:#4caf84; font-weight:700;">Good rains expected</div>
</div>
<div style="background:#0f1820; border-radius:12px; padding:16px 24px; border-left: 3px solid #f0c040;">
<div style="font-family:'Sora',sans-serif; font-size:0.72rem; color:#4a7080; text-transform:uppercase; letter-spacing:2px; margin-bottom:4px;">Near Normal</div>
<div style="font-family:'Playfair Display',serif; font-size:1.1rem; color:#f0c040; font-weight:700;">Average season likely</div>
</div>
<div style="background:#0f1820; border-radius:12px; padding:16px 24px; border-left: 3px solid #e05252;">
<div style="font-family:'Sora',sans-serif; font-size:0.72rem; color:#4a7080; text-transform:uppercase; letter-spacing:2px; margin-bottom:4px;">Below Normal</div>
<div style="font-family:'Playfair Display',serif; font-size:1.1rem; color:#e05252; font-weight:700;">Drought risk — prepare now</div>
</div>
</div>
</div>
</section>
""", unsafe_allow_html=True)


# ── Validation ────────────────────────────────────────────────────
st.markdown("""
<section class="validation-section">
<span class="section-tag" style="display:block; text-align:center; margin-bottom:48px">Validated Against History</span>
<div class="validation-grid">
<div class="val-card">
<div class="val-headline">HSS +0.063</div>
<div class="val-subline">Kiremt prospective skill (rolling-origin) · HSS 0.145 leave-one-out</div>
<p class="val-detail">Validated using two complementary methods. <b>Rolling-origin</b> (train 1981–T, forecast T+1 for 27 test seasons) gives Kiremt HSS +0.063 — the conservative, prospective metric that uses only past data. <b>Leave-one-out cross-validation</b> (LOOCV, 42 years) gives Kiremt HSS 0.145. 4 Kiremt regions (Benishangul-Gumz, Somali, Harari, Tigray) meet the Full forecast threshold (rolling-origin HSS ≥ 0.10). Per-region release tiers are shown in the Validation tab.</p>
<div class="drought-years" style="margin-top:20px">
<span class="correct-badge">39.8% overall accuracy</span>
<span class="correct-badge">53.0% drought detection</span>
<span class="correct-badge">1,092 verified forecasts</span>
<span class="correct-badge">42 years validated</span>
</div>
</div>
<div class="val-card">
<div class="val-headline">298</div>
<div class="val-subline">Drought cases verified across 42 years and 13 regions</div>
<p class="val-detail">ENSO-driven droughts are detectable months in advance from ocean signals. The 2002 El Niño food crisis was flagged across 80% of affected regions. The 1984 famine year — a neutral-year drought with no large-scale ocean precursor — was still detected in 56% of regions. Neutral-year droughts remain a fundamental challenge for all statistical forecast systems globally, including ICPAC and ECMWF.</p>
<div class="drought-years">
<span class="correct-badge">2002 El Niño — 80% detected</span>
<span class="correct-badge">1984 famine year — 56% detected</span>
<span class="drought-badge">2009 La Niña — 33% detected</span>
<span class="drought-badge">2015 El Niño — 20% detected</span>
</div>
</div>
</div>
</section>
""", unsafe_allow_html=True)


# ── Methodology ───────────────────────────────────────────────────
st.markdown("""
<section style="padding: 100px 40px; max-width: 1100px; margin: 0 auto;">
<span class="section-tag" style="display:block; text-align:center; margin-bottom:16px">Under the Hood</span>
<h2 style="font-family: 'Playfair Display', serif; font-size: clamp(2rem, 4vw, 2.8rem); font-weight: 700; color: #f0f8f0; text-align: center; margin-bottom: 16px; letter-spacing: -0.5px;">Rigorous Science. Transparent Methods.</h2>
<p style="font-family: 'Sora', sans-serif; font-size: 1rem; color: #7a9aaa; text-align: center; max-width: 640px; margin: 0 auto 64px auto; line-height: 1.8;">Azmera is built on established climate science and open, institutional data — not a black box. Here is exactly how it works.</p>
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
<div style="background: #080e1a; border: 1px solid #0f1e2e; border-radius: 20px; padding: 36px; grid-column: 1 / -1;">
<div style="margin-bottom: 16px;">
<div style="font-family: 'Sora', sans-serif; font-size: 0.72rem; font-weight: 600; letter-spacing: 3px; text-transform: uppercase; color: #4a9060; margin-bottom: 6px;">Core Model</div>
<div style="font-family: 'Playfair Display', serif; font-size: 1.3rem; font-weight: 700; color: #c8e0d8;">Logistic Regression — 156 Zone Models</div>
</div>
<p style="font-family: 'Sora', sans-serif; font-size: 0.92rem; color: #7a9aaa; line-height: 1.8;">Azmera uses <b style="color:#c8e0d8">Logistic Regression (L2 regularised, C=0.5)</b> — the method recommended by climate forecasting literature for small datasets (Wilks 2006, Weigel et al. 2008), with well-calibrated probabilities and transparent, explainable outputs critical for a food security tool. 156 models are trained: one per zone per season, using <b style="color:#c8e0d8">44 years</b> of CHIRPS 5km satellite rainfall records (1981–2022). LR was selected over XGBoost and Random Forest after head-to-head LOOCV comparison — simpler regularised models generalise better with approximately 42 training samples per zone.</p>
</div>
<div style="background: #080e1a; border: 1px solid #0f1e2e; border-radius: 20px; padding: 36px;">
<div style="font-family: 'Sora', sans-serif; font-size: 0.72rem; font-weight: 600; letter-spacing: 3px; text-transform: uppercase; color: #4a9060; margin-bottom: 8px;">Input Features</div>
<div style="font-family: 'Playfair Display', serif; font-size: 1.2rem; font-weight: 700; color: #c8e0d8; margin-bottom: 12px;">5 Ocean Climate Signals</div>
<p style="font-family: 'Sora', sans-serif; font-size: 0.88rem; color: #7a9aaa; line-height: 1.8;">ENSO (Niño 3.4), Indian Ocean Dipole, Pacific Decadal Oscillation, Atlantic SST — each with lag features — and Atlantic Meridional Mode (AMM Jan) for select Belg regions (Phase F). These ocean-atmosphere signals are the primary drivers of Ethiopian seasonal rainfall variability.</p>
</div>
<div style="background: #080e1a; border: 1px solid #0f1e2e; border-radius: 20px; padding: 36px;">
<div style="font-family: 'Sora', sans-serif; font-size: 0.72rem; font-weight: 600; letter-spacing: 3px; text-transform: uppercase; color: #4a9060; margin-bottom: 8px;">Training and Validation</div>
<div style="font-family: 'Playfair Display', serif; font-size: 1.2rem; font-weight: 700; color: #c8e0d8; margin-bottom: 12px;">Leave-One-Out Cross Validation</div>
<p style="font-family: 'Sora', sans-serif; font-size: 0.88rem; color: #7a9aaa; line-height: 1.8;">For each of the 42 years (1981–2022), the model was retrained on all other years and tested on the held-out year — the standard WMO/ICPAC verification approach. Overall accuracy 44.2%, Kiremt HSS 0.316. No year was ever used to both train and test.</p>
</div>
<div style="background: #080e1a; border: 1px solid #0f1e2e; border-radius: 20px; padding: 36px;">
<div style="font-family: 'Sora', sans-serif; font-size: 0.72rem; font-weight: 600; letter-spacing: 3px; text-transform: uppercase; color: #4a9060; margin-bottom: 8px;">Data Sources</div>
<div style="font-family: 'Playfair Display', serif; font-size: 1.2rem; font-weight: 700; color: #c8e0d8; margin-bottom: 12px;">100% Open and Free</div>
<p style="font-family: 'Sora', sans-serif; font-size: 0.88rem; color: #7a9aaa; line-height: 1.8;">CHIRPS 5km satellite rainfall · NOAA climate indices · WFP / HDX market prices. No proprietary data subscriptions. No vendor lock-in. Fully reproducible and auditable by any researcher or institution.</p>
</div>
<div style="background: #080e1a; border: 1px solid #0f1e2e; border-radius: 20px; padding: 36px;">
<div style="font-family: 'Sora', sans-serif; font-size: 0.72rem; font-weight: 600; letter-spacing: 3px; text-transform: uppercase; color: #4a9060; margin-bottom: 8px;">Output</div>
<div style="font-family: 'Playfair Display', serif; font-size: 1.2rem; font-weight: 700; color: #c8e0d8; margin-bottom: 12px;">Probabilistic Tercile Forecast</div>
<p style="font-family: 'Sora', sans-serif; font-size: 0.88rem; color: #7a9aaa; line-height: 1.8;">Forecasts are expressed as probabilities across three outcomes — Below Normal, Near Normal, Above Normal — consistent with the standard format used by ICPAC and WMO regional climate centers. No false precision. No single-number predictions.</p>
</div>
</div>
</section>
""", unsafe_allow_html=True)


# ── Audience ──────────────────────────────────────────────────────
st.markdown("""
<section class="audience-section">
<div class="audience-inner">
<h2 class="audience-title">Built for Every Stakeholder</h2>
<div class="audience-grid">
<div class="audience-card">
<div class="audience-role">Farmers</div>
<div class="audience-title-sm">Plain language. Local crops. Amharic.</div>
<p class="audience-desc">Know whether to plant drought-tolerant Sorghum (Mashilla) or higher-yield Teff this season. Get water preparation advice 3 months before the rains. Forecasts available at the zone level — specific to your woreda, not just your region.</p>
</div>
<div class="audience-card">
<div class="audience-role">NGOs and Humanitarian Orgs</div>
<div class="audience-title-sm">Early warning. Zone-specific. Free.</div>
<p class="audience-desc">Integrate Azmera's zone-level drought probabilities into food security response planning. 78 zones across Ethiopia, each with its own calibrated forecast. Combines climate outlooks with live WFP market price data — all from a single dashboard.</p>
</div>
<div class="audience-card">
<div class="audience-role">Government and Policy</div>
<div class="audience-title-sm">78 zones. 2 seasons. Reproducible.</div>
<p class="audience-desc">Seasonal outlooks for all 78 Ethiopian zones across both Kiremt and Belg seasons. Validated against 44 years of historical data using WMO-standard LOOCV. Interactive risk map with region to zone drill-down. Complementary to ICPAC and NMA forecasts.</p>
</div>
<div class="audience-card">
<div class="audience-role">Investors and Partners</div>
<div class="audience-title-sm">Scalable. Open data. Impact-driven.</div>
<p class="audience-desc">Built entirely on free, open data sources — CHIRPS, NOAA, WFP HDX. No proprietary data dependencies. Zone-level granularity with interactive mapping. Designed to integrate with existing agritech platforms as a forecasting engine.</p>
</div>
</div>
</div>
</section>
""", unsafe_allow_html=True)

# ── Final CTA ─────────────────────────────────────────────────────
st.markdown("""
<section class="final-cta">
<h2 class="final-title">The harvest begins<br>with a forecast.</h2>
<p class="final-sub" style="text-align:center; margin-left:auto; margin-right:auto;">Select your region or zone, choose your season, and get a seasonal rainfall outlook with farmer-ready crop recommendations — in under 30 seconds.</p>
<div class="hero-cta-group">
<a href="https://azmera-forecast.streamlit.app" target="_blank" class="cta-primary">Open Azmera Forecast</a>
</div>
<div class="data-sources">
<span class="source-pill">CHIRPS 5km Satellite</span>
<span class="source-pill">NOAA Climate Indices</span>
<span class="source-pill">WFP / HDX Market Prices</span>
<span class="source-pill">156 Zone Models</span>
<span class="source-pill">Interactive Zone Map</span>
<span class="source-pill">CHIRPS Observed Rainfall</span>
<span class="source-pill">Amharic Advisory</span>
</div>
</section>
""", unsafe_allow_html=True)