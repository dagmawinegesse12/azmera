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

html, body, .stApp {
    background-color: #05080f;
    color: #e0e8f0;
}

.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* ── Hero ── */
.hero {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    padding: 80px 40px;
    position: relative;
    overflow: hidden;
    background:
        radial-gradient(ellipse 80% 60% at 50% 0%, rgba(16,80,40,0.35) 0%, transparent 70%),
        radial-gradient(ellipse 60% 40% at 20% 80%, rgba(10,40,80,0.3) 0%, transparent 60%),
        #05080f;
}

.hero::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image:
        radial-gradient(circle at 1px 1px, rgba(255,255,255,0.04) 1px, transparent 0);
    background-size: 40px 40px;
    pointer-events: none;
}

.hero-eyebrow {
    font-family: 'Sora', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: #4a9060;
    margin-bottom: 24px;
    animation: fadeUp 0.8s ease both;
}

.hero-title {
    font-family: 'Playfair Display', serif;
    font-size: clamp(3rem, 8vw, 7rem);
    font-weight: 900;
    line-height: 1.0;
    letter-spacing: -2px;
    color: #f0f8f0;
    margin-bottom: 12px;
    animation: fadeUp 0.8s ease 0.1s both;
}

.hero-title-amharic {
    font-family: 'Noto Sans Ethiopic', sans-serif;
    font-size: clamp(1.5rem, 4vw, 3rem);
    font-weight: 400;
    color: #4a9060;
    letter-spacing: 0;
    margin-bottom: 32px;
    animation: fadeUp 0.8s ease 0.2s both;
}

.hero-subtitle {
    font-family: 'Sora', sans-serif;
    font-size: clamp(1rem, 2vw, 1.25rem);
    font-weight: 300;
    color: #8aacb0;
    max-width: 640px;
    line-height: 1.8;
    margin-bottom: 48px;
    animation: fadeUp 0.8s ease 0.3s both;
}

.hero-cta-group {
    display: flex;
    gap: 16px;
    justify-content: center;
    flex-wrap: wrap;
    animation: fadeUp 0.8s ease 0.4s both;
}

.cta-primary {
    background: linear-gradient(135deg, #1a6b40, #27ae60);
    color: white;
    font-family: 'Sora', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    padding: 16px 40px;
    border-radius: 100px;
    text-decoration: none;
    letter-spacing: 0.5px;
    box-shadow: 0 8px 32px rgba(39,174,96,0.3);
    transition: all 0.3s ease;
    display: inline-block;
}

.cta-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(39,174,96,0.5);
    color: white;
    text-decoration: none;
}

.cta-secondary {
    background: transparent;
    color: #8aacb0;
    font-family: 'Sora', sans-serif;
    font-size: 1rem;
    font-weight: 400;
    padding: 16px 32px;
    border-radius: 100px;
    border: 1px solid #1e3040;
    text-decoration: none;
    transition: all 0.3s ease;
    display: inline-block;
}

.cta-secondary:hover {
    border-color: #4a9060;
    color: #4a9060;
    text-decoration: none;
}

/* ── Stats strip ── */
.stats-strip {
    display: flex;
    justify-content: center;
    gap: 0;
    margin-top: 80px;
    animation: fadeUp 0.8s ease 0.5s both;
    border-top: 1px solid #0f1820;
    border-bottom: 1px solid #0f1820;
    width: 100%;
    max-width: 800px;
}

.stat-item {
    flex: 1;
    padding: 24px 32px;
    text-align: center;
    border-right: 1px solid #0f1820;
}

.stat-item:last-child { border-right: none; }

.stat-number {
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    font-weight: 700;
    color: #4a9060;
    display: block;
}

.stat-label {
    font-family: 'Sora', sans-serif;
    font-size: 0.75rem;
    color: #4a6070;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-top: 4px;
    display: block;
}

/* ── Story section ── */
.story-section {
    padding: 120px 40px;
    max-width: 1100px;
    margin: 0 auto;
}

.section-tag {
    font-family: 'Sora', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: #4a9060;
    margin-bottom: 20px;
    display: block;
}

.story-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 80px;
    align-items: center;
}

.story-headline {
    font-family: 'Playfair Display', serif;
    font-size: clamp(2rem, 4vw, 3rem);
    font-weight: 700;
    color: #f0f8f0;
    line-height: 1.2;
    letter-spacing: -0.5px;
    margin-bottom: 24px;
}

.story-body {
    font-family: 'Sora', sans-serif;
    font-size: 1rem;
    color: #7a9aaa;
    line-height: 1.9;
    margin-bottom: 20px;
}

.story-body strong {
    color: #c8e0d8;
}

.story-quote {
    border-left: 3px solid #4a9060;
    padding: 20px 24px;
    background: rgba(26, 107, 64, 0.08);
    border-radius: 0 12px 12px 0;
    margin: 32px 0;
    font-family: 'Playfair Display', serif;
    font-size: 1.15rem;
    color: #c8e0d8;
    line-height: 1.7;
    font-style: italic;
}

/* ── How it works ── */
.how-section {
    padding: 100px 40px;
    background: linear-gradient(180deg, #05080f 0%, #070d18 50%, #05080f 100%);
}

.how-inner {
    max-width: 1100px;
    margin: 0 auto;
}

.how-title {
    font-family: 'Playfair Display', serif;
    font-size: clamp(2rem, 4vw, 2.8rem);
    font-weight: 700;
    color: #f0f8f0;
    text-align: center;
    margin-bottom: 64px;
    letter-spacing: -0.5px;
}

.steps-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 32px;
}

.step-card {
    background: #080e1a;
    border: 1px solid #0f1e2e;
    border-radius: 20px;
    padding: 36px 32px;
    position: relative;
    transition: border-color 0.3s ease;
}

.step-card:hover {
    border-color: #1a5030;
}

.step-number {
    font-family: 'Playfair Display', serif;
    font-size: 3rem;
    font-weight: 900;
    color: #0f2018;
    position: absolute;
    top: 20px;
    right: 24px;
    line-height: 1;
}

.step-icon {
    font-size: 2rem;
    margin-bottom: 16px;
    display: block;
}

.step-title {
    font-family: 'Sora', sans-serif;
    font-size: 1.05rem;
    font-weight: 600;
    color: #c8e0d8;
    margin-bottom: 10px;
}

.step-desc {
    font-family: 'Sora', sans-serif;
    font-size: 0.88rem;
    color: #4a7080;
    line-height: 1.7;
}

/* ── Validation section ── */
.validation-section {
    padding: 100px 40px;
    max-width: 1100px;
    margin: 0 auto;
}

.validation-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 48px;
    align-items: start;
}

.val-card {
    background: #080e1a;
    border: 1px solid #0f1e2e;
    border-radius: 20px;
    padding: 40px;
}

.val-headline {
    font-family: 'Playfair Display', serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: #4a9060;
    margin-bottom: 8px;
}

.val-subline {
    font-family: 'Sora', sans-serif;
    font-size: 0.85rem;
    color: #4a7080;
    margin-bottom: 20px;
}

.val-detail {
    font-family: 'Sora', sans-serif;
    font-size: 0.92rem;
    color: #7a9aaa;
    line-height: 1.7;
}

.drought-years {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 16px;
}

.drought-badge {
    background: rgba(192, 57, 43, 0.15);
    border: 1px solid rgba(192, 57, 43, 0.3);
    color: #e74c3c;
    font-family: 'Sora', sans-serif;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 100px;
}

.correct-badge {
    background: rgba(39, 174, 96, 0.15);
    border: 1px solid rgba(39, 174, 96, 0.3);
    color: #27ae60;
    font-family: 'Sora', sans-serif;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 100px;
}

/* ── Audience section ── */
.audience-section {
    padding: 100px 40px;
    background: #070d18;
}

.audience-inner {
    max-width: 1100px;
    margin: 0 auto;
}

.audience-title {
    font-family: 'Playfair Display', serif;
    font-size: clamp(2rem, 4vw, 2.8rem);
    font-weight: 700;
    color: #f0f8f0;
    text-align: center;
    margin-bottom: 56px;
}

.audience-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 24px;
}

.audience-card {
    background: #05080f;
    border: 1px solid #0f1e2e;
    border-radius: 20px;
    padding: 36px;
    transition: border-color 0.3s ease;
}

.audience-card:hover {
    border-color: #1a5030;
}

.audience-icon {
    font-size: 2rem;
    margin-bottom: 16px;
    display: block;
}

.audience-role {
    font-family: 'Sora', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #4a9060;
    margin-bottom: 8px;
}

.audience-title-sm {
    font-family: 'Playfair Display', serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: #c8e0d8;
    margin-bottom: 12px;
}

.audience-desc {
    font-family: 'Sora', sans-serif;
    font-size: 0.88rem;
    color: #4a7080;
    line-height: 1.7;
}

/* ── Final CTA ── */
.final-cta {
    padding: 140px 40px;
    text-align: center;
    position: relative;
    overflow: hidden;
    background:
        radial-gradient(ellipse 70% 50% at 50% 50%, rgba(16,80,40,0.2) 0%, transparent 70%),
        #05080f;
}

.final-title {
    font-family: 'Playfair Display', serif;
    font-size: clamp(2.5rem, 5vw, 4.5rem);
    font-weight: 900;
    color: #f0f8f0;
    letter-spacing: -1px;
    margin-bottom: 20px;
    line-height: 1.1;
}

.final-sub {
    font-family: 'Sora', sans-serif;
    font-size: 1.1rem;
    color: #7a9aaa;
    max-width: 520px;
    margin: 0 auto 48px auto;
    line-height: 1.7;
}

.data-sources {
    display: flex;
    justify-content: center;
    gap: 24px;
    flex-wrap: wrap;
    margin-top: 64px;
}

.source-pill {
    background: #080e1a;
    border: 1px solid #0f1e2e;
    border-radius: 100px;
    padding: 8px 20px;
    font-family: 'Sora', sans-serif;
    font-size: 0.75rem;
    color: #4a7080;
    letter-spacing: 0.5px;
}

/* Animations */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(24px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* Responsive */
@media (max-width: 768px) {
    .story-grid, .steps-grid, .validation-grid, .audience-grid {
        grid-template-columns: 1fr;
        gap: 32px;
    }
    .stats-strip { flex-direction: column; }
    .stat-item { border-right: none; border-bottom: 1px solid #0f1820; }
}
</style>
""", unsafe_allow_html=True)


# ── Hero ──────────────────────────────────────────────────────────
st.markdown("""
<section class="hero">
    <span class="hero-eyebrow">🌾 Introducing Azmera</span>
    <h1 class="hero-title">Know Before<br>the Rains Fail</h1>
    <p class="hero-title-amharic">አዝመራ — Harvest</p>
    <p class="hero-subtitle">
        AI-powered seasonal rainfall forecasting for Ethiopian farmers,
        humanitarian organizations, and policymakers —
        up to 3 months before the growing season begins.
    </p>
    <div class="hero-cta-group">
        <a href="https://azmera-forecast.streamlit.app" target="_self" class="cta-primary">
            🔮 Try Azmera Now →
        </a>
        <a href="#story" class="cta-secondary">
            Read the Story
        </a>
    </div>
    <div class="stats-strip">
        <div class="stat-item">
            <span class="stat-number">44</span>
            <span class="stat-label">Years of Data</span>
        </div>
        <div class="stat-item">
            <span class="stat-number">13</span>
            <span class="stat-label">Ethiopian Regions</span>
        </div>
        <div class="stat-item">
            <span class="stat-number">100%</span>
            <span class="stat-label">2015 Drought Precision</span>
        </div>
        <div class="stat-item">
            <span class="stat-number">4</span>
            <span class="stat-label">Ocean Signals Analyzed</span>
        </div>
    </div>
</section>
""", unsafe_allow_html=True)


# ── Story Section ─────────────────────────────────────────────────
st.markdown("""
<section class="story-section" id="story">
    <div class="story-grid">
        <div>
            <span class="section-tag">Why Azmera Exists</span>
            <h2 class="story-headline">The 1997 drought changed Ethiopia. We're making sure the next one doesn't catch anyone off guard.</h2>
        </div>
        <div>
            <p class="story-body">
                In 1997, a powerful El Niño triggered one of Ethiopia's most devastating droughts.
                Crops failed. Livestock died. Millions faced food insecurity across the Horn of Africa.
                It is the drought that <strong>most Ethiopians alive today remember</strong> — not because
                it was the worst in history, but because it struck without adequate warning reaching
                the farmers who needed it most.
            </p>
            <p class="story-body">
                Ethiopia has world-class climate scientists at ICPAC and the National Meteorological
                Institute. But their forecasts are written for policymakers — not for a farmer
                in Oromia deciding whether to plant Teff or Sorghum next month.
            </p>
            <div class="story-quote">
                "The science exists. The data exists. What's missing is the last mile —
                turning climate forecasts into decisions farmers can actually act on."
            </div>
            <p class="story-body">
                Azmera bridges that gap. Built by an Ethiopian engineer using NASA satellite data,
                NOAA ocean indices, and 44 years of rainfall records — translated into plain language,
                <strong>in Amharic</strong>, for the people who need it most.
            </p>
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
                <span class="step-number">01</span>
                <span class="step-icon">🌊</span>
                <div class="step-title">Read the Ocean Signals</div>
                <p class="step-desc">
                    Azmera monitors 4 global climate indices in real time —
                    El Niño / La Niña (ENSO), the Indian Ocean Dipole (IOD),
                    the Pacific Decadal Oscillation (PDO), and Atlantic sea
                    surface temperatures. These ocean patterns drive Ethiopian
                    rainfall months before the season begins.
                </p>
            </div>
            <div class="step-card">
                <span class="step-number">02</span>
                <span class="step-icon">🤖</span>
                <div class="step-title">Run the AI Forecast Model</div>
                <p class="step-desc">
                    An XGBoost machine learning model trained on 44 years of
                    NASA POWER rainfall data predicts whether the upcoming
                    Kiremt or Belg season will be below normal, near normal,
                    or above normal — for each of Ethiopia's 13 regions
                    separately.
                </p>
            </div>
            <div class="step-card">
                <span class="step-number">03</span>
                <span class="step-icon">🌾</span>
                <div class="step-title">Deliver Actionable Guidance</div>
                <p class="step-desc">
                    Farmers receive plain-language crop recommendations —
                    which Ethiopian crops to plant, when to plant them,
                    how to prepare water storage — in both English and
                    Amharic. Alongside live WFP market prices for Teff,
                    Maize, Sorghum, Wheat, and Barley.
                </p>
            </div>
        </div>
    </div>
</section>
""", unsafe_allow_html=True)


# ── Validation ────────────────────────────────────────────────────
st.markdown("""
<section class="validation-section">
    <span class="section-tag" style="display:block; text-align:center; margin-bottom:48px">
        Validated Against History
    </span>
    <div class="validation-grid">
        <div class="val-card">
            <div class="val-headline">4 / 4</div>
            <div class="val-subline">Drought regions correctly flagged — 2015 Kiremt season</div>
            <p class="val-detail">
                During Ethiopia's worst drought in 50 years, Azmera's model correctly
                identified all four drought-affected regions with high confidence
                (60–80% drought probability) and <strong style="color:#27ae60">zero false alarms</strong>.
                Somali and Benishangul-Gumz — which received above-normal rainfall —
                were correctly NOT flagged.
            </p>
            <div class="drought-years" style="margin-top:20px">
                <span class="correct-badge">✅ Afar — 80%</span>
                <span class="correct-badge">✅ Amhara — 69%</span>
                <span class="correct-badge">✅ Oromia — 60%</span>
                <span class="correct-badge">✅ Gambela — 57%</span>
            </div>
        </div>
        <div class="val-card">
            <div class="val-headline">61.5%</div>
            <div class="val-subline">Accuracy during strong ENSO signals</div>
            <p class="val-detail">
                When El Niño or La Niña conditions are strong — exactly when droughts
                are most likely — Azmera achieves 61.5% accuracy. The model correctly
                flagged major drought events across Oromia consistently:
            </p>
            <div class="drought-years">
                <span class="drought-badge">2000–2005 drought</span>
                <span class="drought-badge">2009 drought</span>
                <span class="drought-badge">2011 drought</span>
                <span class="drought-badge">2015 El Niño</span>
                <span class="correct-badge">All correctly flagged</span>
            </div>
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
                <span class="audience-icon">👨‍🌾</span>
                <div class="audience-role">Farmers</div>
                <div class="audience-title-sm">Plain language. Local crops. Amharic.</div>
                <p class="audience-desc">
                    Know whether to plant drought-tolerant Sorghum (Mashilla) or
                    higher-yield Teff this season. Get water preparation advice
                    3 months before the rains. No climate science degree required.
                </p>
            </div>
            <div class="audience-card">
                <span class="audience-icon">🏛️</span>
                <div class="audience-role">NGOs & Humanitarian Orgs</div>
                <div class="audience-title-sm">Early warning. Region-specific. Free.</div>
                <p class="audience-desc">
                    Integrate Azmera's regional drought probabilities into food
                    security response planning. Combines climate forecasts with
                    live WFP market price data — all from a single dashboard.
                </p>
            </div>
            <div class="audience-card">
                <span class="audience-icon">🏛️</span>
                <div class="audience-role">Government & Policy</div>
                <div class="audience-title-sm">13 regions. 2 seasons. Reproducible.</div>
                <p class="audience-desc">
                    Seasonal outlooks for all 13 Ethiopian administrative regions,
                    for both Kiremt and Belg seasons. Validated against 44 years
                    of historical data. Complementary to ICPAC and NMA forecasts.
                </p>
            </div>
            <div class="audience-card">
                <span class="audience-icon">💡</span>
                <div class="audience-role">Investors & Partners</div>
                <div class="audience-title-sm">Scalable. Open data. Impact-driven.</div>
                <p class="audience-desc">
                    Built entirely on free, open data sources — NASA, NOAA, WFP HDX.
                    No proprietary data dependencies. Designed to integrate with
                    existing agritech platforms like Lersha as a forecasting engine.
                </p>
            </div>
        </div>
    </div>
</section>
""", unsafe_allow_html=True)


# ── Final CTA ─────────────────────────────────────────────────────
st.markdown("""
<section class="final-cta">
    <h2 class="final-title">The harvest begins<br>with a forecast.</h2>
    <p class="final-sub" style="text-align:center; margin-left:auto; margin-right:auto;">
        Select your region, choose your season, and get an AI-powered
        rainfall outlook with farmer-ready crop recommendations —
        in under 30 seconds.
    </p>
    <div class="hero-cta-group">
        <a href="https://azmera-forecast.streamlit.app" target="_self" class="cta-primary">
            🔮 Open Azmera Forecast →
        </a>
    </div>
    <div class="data-sources">
        <span class="source-pill">📡 NASA POWER</span>
        <span class="source-pill">🌊 NOAA Climate Indices</span>
        <span class="source-pill">🌾 WFP / HDX Market Prices</span>
        <span class="source-pill">🤖 XGBoost ML Model</span>
        <span class="source-pill">🗣️ OpenAI Amharic Advisory</span>
    </div>
</section>
""", unsafe_allow_html=True)