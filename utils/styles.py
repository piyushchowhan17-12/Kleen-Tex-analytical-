"""
CSS styles — dark navy / teal / amber design matching HTML reference.
"""

import streamlit as st


def inject_css():
    st.markdown(
        """
<style>
/* ═══════════════════════════════════════════════════════
   IMPORT FONTS
══════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,600;1,9..144,300&family=Inter:wght@300;400;500;600&family=DM+Sans:wght@300;400;500&display=swap');

/* ═══════════════════════════════════════════════════════
   DESIGN TOKENS
══════════════════════════════════════════════════════ */
:root {
  --navy:    #0d1b2a;
  --navy2:   #1a2e45;
  --navy3:   #243b55;
  --teal:    #1bb8a0;
  --teal2:   #0d9b87;
  --teal3:   #08705f;
  --amber:   #f5a623;
  --rose:    #e05c7a;
  --slate:   #8fa3b8;
  --slate2:  #6b859e;
  --white:   #f4f8fb;
  --white2:  #dde8f0;
  --text:    #f4f8fb;
  --text2:   #a8c0d4;
  --text3:   #6b859e;
  --card:    #162535;
  --card2:   #1d3048;
  --border:  #243b55;
  --r:       10px;
  --r2:      6px;
  --shadow:  0 4px 24px rgba(0,0,0,0.35);
  --sidebar-w: 220px;
}

/* ═══════════════════════════════════════════════════════
   GLOBAL RESET & BASE
══════════════════════════════════════════════════════ */
html, body, .stApp {
    background-color: var(--navy) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden !important; }
.block-container {
    padding: 1.5rem 2rem !important;
    max-width: 1600px !important;
}

/* ═══════════════════════════════════════════════════════
   SIDEBAR — narrow, centered nav like HTML reference
══════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {
    background-color: var(--navy2) !important;
    border-right: 1px solid var(--border) !important;
    min-width: var(--sidebar-w) !important;
    max-width: var(--sidebar-w) !important;
    width:     var(--sidebar-w) !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding: 0 !important;
    min-width: var(--sidebar-w) !important;
    max-width: var(--sidebar-w) !important;
    width:     var(--sidebar-w) !important;
}
/* Hide ALL sidebar collapse/expand controls — sidebar is permanently fixed */
button[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] button {
    display: none !important;
    pointer-events: none !important;
}

/* ── Brand block ── */
.brand-block {
    padding: 22px 20px 18px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 4px;
    text-align: left;
}
.brand-title {
    font-family: 'Inter', 'DM Sans', sans-serif;
    font-weight: 600;
    font-size: 20px;
    color: var(--white);
    line-height: 1.25;
    letter-spacing: -0.02em;
}
.brand-sub {
    font-family: 'Inter', 'DM Sans', sans-serif;
    font-weight: 400;
    font-size: 15px;
    color: var(--slate);
    margin-top: 4px;
    letter-spacing: .06em;
    display: block;
}

/* ── Nav section label ── */
.nav-section-label {
    font-size: 16px;
    text-transform: uppercase;
    letter-spacing: .16em;
    color: var(--slate2);
    font-weight: 600;
    font-family: 'Inter', 'DM Sans', sans-serif;
    padding: 18px 20px 6px;
    text-align: left;
}

/* ── Nav buttons — left-aligned icon+label style ── */
section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: none !important;
    border-left: 3px solid transparent !important;
    color: var(--slate) !important;
    font-family: 'Inter', 'DM Sans', sans-serif !important;
    font-size: 20px !important;
    font-weight: 500 !important;
    text-align: left !important;
    justify-content: flex-start !important;
    display: flex !important;
    align-items: center !important;
    padding: 13px 20px !important;
    border-radius: 0 !important;
    transition: all .15s ease !important;
    width: 100% !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    line-height: 1.4 !important;
    letter-spacing: 0.01em !important;
}
section[data-testid="stSidebar"] .stButton > button p,
section[data-testid="stSidebar"] .stButton > button div,
section[data-testid="stSidebar"] .stButton > button span {
    text-align: left !important;
    font-size: 20px !important;
    width: 100% !important;
    margin: 0 !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(27,184,160,0.06) !important;
    color: var(--white) !important;
    border-left: 3px solid var(--slate2) !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: rgba(27,184,160,0.08) !important;
    color: var(--teal) !important;
    border-left: 3px solid var(--teal) !important;
    font-weight: 600 !important;
}
section[data-testid="stSidebar"] .stButton > button:disabled {
    color: var(--slate2) !important;
    opacity: 0.38 !important;
    cursor: not-allowed !important;
    font-weight: 400 !important;
}

/* Icon character — slightly larger, monospace feel, matches screenshot weight */
section[data-testid="stSidebar"] .stButton > button::first-letter {
    font-size: 16px;
    font-weight: 300;
    opacity: 0.85;
    margin-right: 2px;
    font-family: 'Inter', monospace !important;
}

/* ── Status & footer ── */
.status-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 16px;
    font-size: 14px;
    color: var(--text2);
    font-family: 'Inter', 'DM Sans', sans-serif;
}
.sidebar-info {
    padding: 4px 16px;
    font-size: 11px;
    color: var(--teal);
    font-family: 'DM Mono', monospace;
}
.sidebar-footer {
    padding: 10px 16px;
    font-size: 12px;
    color: var(--slate2);
    border-top: 1px solid var(--border);
    margin-top: 10px;
    text-align: center;
    font-family: 'Inter', 'DM Sans', sans-serif;
}

/* ═══════════════════════════════════════════════════════
   PAGE HEADER / TOPBAR
══════════════════════════════════════════════════════ */
.topbar {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--r);
    padding: 16px 22px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.topbar-title {
    font-family: 'Fraunces', serif;
    font-weight: 300;
    font-size: 30px;
    color: var(--white);
}
.topbar-sub {
    font-size: 12px;
    color: var(--slate);
    margin-top: 3px;
}
.badge-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 500;
    font-family: 'DM Mono', monospace;
}
.pill-teal  { background: rgba(27,184,160,.15); color: var(--teal); border: 1px solid rgba(27,184,160,.3); }
.pill-amber { background: rgba(245,166,35,.12); color: var(--amber); border: 1px solid rgba(245,166,35,.25); }
.pill-rose  { background: rgba(224,92,122,.12); color: var(--rose); border: 1px solid rgba(224,92,122,.25); }
.pill-slate { background: rgba(107,133,158,.12); color: var(--slate); border: 1px solid rgba(107,133,158,.25); }

/* ═══════════════════════════════════════════════════════
   CARDS
══════════════════════════════════════════════════════ */
.sc-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--r);
    padding: 18px 20px;
    margin-bottom: 18px;
}
.sc-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
}
.sc-card-title {
    font-family: 'Fraunces', serif;
    font-weight: 300;
    font-size: 20px;
    color: var(--white);
}
.sc-card-sub {
    font-size: 16px;
    color: var(--slate);
    margin-top: 2px;
}

/* ═══════════════════════════════════════════════════════
   METRIC TILES
══════════════════════════════════════════════════════ */
.metric-tile {
    background: var(--card2);
    border: 1px solid var(--border);
    border-radius: var(--r2);
    padding: 16px 18px;
}
.metric-tile.accent-teal  { border-left: 3px solid var(--teal); }
.metric-tile.accent-amber { border-left: 3px solid var(--amber); }
.metric-tile.accent-rose  { border-left: 3px solid var(--rose); }
.metric-tile.accent-slate { border-left: 3px solid var(--slate); }
.metric-label {
    font-size: 16px;
    color: var(--text3);
    text-transform: uppercase;
    letter-spacing: .07em;
    margin-bottom: 6px;
}
.metric-value {
    font-family: 'DM Mono', monospace;
    font-size: 28px;
    font-weight: 500;
    color: var(--white);
}
.metric-sub {
    font-size: 14px;
    color: var(--slate);
    margin-top: 3px;
}

/* ═══════════════════════════════════════════════════════
   STEP ROWS
══════════════════════════════════════════════════════ */
.step-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 10px;
    padding: 12px;
    background: var(--card2);
    border-radius: var(--r2);
    border: 1px solid var(--border);
}
.step-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: var(--teal);
    color: var(--navy);
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 1px;
}
.step-title {
    font-weight: 500;
    color: var(--white);
    margin-bottom: 3px;
    font-size: 16px;
}
.step-desc {
    font-size: 16px;
    color: var(--slate);
    line-height: 1.55;
}
.code-tag {
    display: inline-block;
    padding: 1px 6px;
    background: var(--navy3);
    border-radius: 3px;
    font-size: 14px;
    color: var(--amber);
    font-family: 'DM Mono', monospace;
    margin: 1px;
}

/* ═══════════════════════════════════════════════════════
   TABLES
══════════════════════════════════════════════════════ */
.stDataFrame, [data-testid="stDataFrame"] {
    background: var(--card2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r2) !important;
}
.stDataFrame thead tr th {
    background: var(--navy3) !important;
    color: var(--slate) !important;
    font-size: 16px !important;
    text-transform: uppercase !important;
    letter-spacing: .07em !important;
}

/* ═══════════════════════════════════════════════════════
   STREAMLIT WIDGETS RESKIN
══════════════════════════════════════════════════════ */
.stSelectbox > div > div {
    background: var(--card2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r2) !important;
    color: var(--text) !important;
}
.stNumberInput > div > div > input {
    background: var(--card2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: var(--r2) !important;
    font-family: 'DM Mono', monospace !important;
}
.stSlider > div > div > div > div {
    background: var(--teal) !important;
}
[data-testid="stFileUploader"] {
    background: var(--card2) !important;
    border: 1px dashed var(--teal3) !important;
    border-radius: var(--r) !important;
    padding: 20px !important;
}
.stButton > button[kind="primary"] {
    background: var(--teal) !important;
    color: var(--navy) !important;
    border: none !important;
    border-radius: var(--r2) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
}
.stButton > button[kind="primary"]:hover {
    background: var(--teal2) !important;
}
.stButton > button[kind="secondary"] {
    background: transparent !important;
    color: var(--teal) !important;
    border: 1px solid var(--teal) !important;
    border-radius: var(--r2) !important;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(27,184,160,.1) !important;
}
.stTextInput > div > div > input {
    background: var(--card2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: var(--r2) !important;
}
.stSelectbox label, .stNumberInput label, .stSlider label,
.stTextInput label, .stFileUploader label, .stMultiSelect label {
    color: var(--text3) !important;
    font-size: 14px !important;
    text-transform: uppercase !important;
    letter-spacing: .07em !important;
    font-family: 'DM Sans', sans-serif !important;
}
.streamlit-expanderHeader {
    background: var(--card2) !important;
    color: var(--white) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r2) !important;
}
.streamlit-expanderContent {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-top: none !important;
}
.stAlert {
    background: var(--card2) !important;
    border-radius: var(--r2) !important;
}
.stProgress > div > div > div > div {
    background: var(--teal) !important;
}
.stMultiSelect > div > div {
    background: var(--card2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r2) !important;
}

/* ═══════════════════════════════════════════════════════
   BADGES
══════════════════════════════════════════════════════ */
.sbadge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 14px;
    font-weight: 500;
    font-family: 'DM Mono', monospace;
}
.sbadge-teal   { background: rgba(27,184,160,.15); color: var(--teal);  border: 1px solid rgba(27,184,160,.3); }
.sbadge-amber  { background: rgba(245,166,35,.12); color: var(--amber); border: 1px solid rgba(245,166,35,.25); }
.sbadge-rose   { background: rgba(224,92,122,.12); color: var(--rose);  border: 1px solid rgba(224,92,122,.25); }
.sbadge-slate  { background: rgba(107,133,158,.1); color: var(--slate); border: 1px solid rgba(107,133,158,.2); }

/* ═══════════════════════════════════════════════════════
   OPTIMIZATION
══════════════════════════════════════════════════════ */
.opt-result-card {
    background: linear-gradient(135deg, var(--card2), var(--card));
    border: 1px solid var(--teal3);
    border-radius: var(--r);
    padding: 22px;
    text-align: center;
}
.opt-result-val {
    font-family: 'DM Mono', monospace;
    font-size: 36px;
    font-weight: 500;
    color: var(--teal);
    margin: 6px 0;
}
.opt-result-label {
    font-size: 18px;
    color: var(--slate);
    text-transform: uppercase;
    letter-spacing: .07em;
}

/* ═══════════════════════════════════════════════════════
   DIVIDER
══════════════════════════════════════════════════════ */
.sc-divider { height: 1px; background: var(--border); margin: 20px 0; }

/* ═══════════════════════════════════════════════════════
   PLOTLY
══════════════════════════════════════════════════════ */
.js-plotly-plot, .plotly { border-radius: var(--r2) !important; }

/* ═══════════════════════════════════════════════════════
   INFO / WARN / ERROR BOXES
══════════════════════════════════════════════════════ */
.info-box {
    background: rgba(27,184,160,.08);
    border: 1px solid rgba(27,184,160,.25);
    border-radius: var(--r2);
    padding: 12px 16px;
    font-size: 16px;
    color: var(--text2);
    line-height: 1.6;
    margin-bottom: 14px;
}
.warn-box {
    background: rgba(245,166,35,.08);
    border: 1px solid rgba(245,166,35,.25);
    border-radius: var(--r2);
    padding: 12px 16px;
    font-size: 16px;
    color: var(--amber);
    line-height: 1.6;
    margin-bottom: 14px;
}
.error-box {
    background: rgba(224,92,122,.08);
    border: 1px solid rgba(224,92,122,.25);
    border-radius: var(--r2);
    padding: 12px 16px;
    font-size: 16px;
    color: var(--rose);
    line-height: 1.6;
    margin-bottom: 14px;
}

/* ═══════════════════════════════════════════════════════
   SCROLLBAR
══════════════════════════════════════════════════════ */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--navy2); }
::-webkit-scrollbar-thumb { background: var(--navy3); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--slate2); }
</style>
        """,
        unsafe_allow_html=True,
    )
