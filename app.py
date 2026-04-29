"""
Supply Chain Analytics Dashboard — Main Entry Point
"""

import streamlit as st

st.set_page_config(
    page_title="Supply Chain Analytics | Demand Forecasting",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.styles import inject_css
from utils.session import init_session

inject_css()
init_session()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _module_enabled(key: str) -> bool:
    s = st.session_state
    if key == "preprocess": return True
    if key == "forecast":   return s.get("imputed_data") is not None
    if key == "optimize":   return s.get("forecast_input_ready") is True
    return False


def _render_sidebar_status():
    s = st.session_state
    st.markdown('<div class="nav-section-label">STATUS</div>', unsafe_allow_html=True)
    steps = [
        ("Raw Data",     s.get("raw_data")            is not None),
        ("Imputation",   s.get("imputed_data")        is not None),
        ("Forecasting",  s.get("forecast_result")     is not None),
        ("Optimization", s.get("optimization_result") is not None),
    ]
    for label, done in steps:
        icon = "✅" if done else "⬜"
        st.markdown(
            f'<div class="status-row">{icon} {label}</div>',
            unsafe_allow_html=True,
        )
    if s.get("selected_skus"):
        n = len(s["selected_skus"])
        st.markdown(
            f'<div class="sidebar-info">🎯 {n} SKUs</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        '<div class="sidebar-footer">Supply Chain Analytics</div>',
        unsafe_allow_html=True,
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Brand — compact, matches HTML sample
    st.markdown("""
    <div class="brand-block">
        <div class="brand-title">Supply Chain<br>Analytics</div>
        <span class="brand-sub">DEMAND FORECASTING · v2.0</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="nav-section-label">MODULES</div>', unsafe_allow_html=True)

    _modules = [
        ("≡",  "Data Preprocessing",  "preprocess"),
        ("∿",  "Demand Forecasting",  "forecast"),
        ("◎",  "Optimization",         "optimize"),
    ]

    _current = st.session_state.get("active_module", "preprocess")

    for _icon, _label, _key in _modules:
        _is_active  = _current == _key
        _is_enabled = _module_enabled(_key)
        _display    = f"{_icon}  {_label}"

        if _is_enabled:
            if st.button(
                _display,
                key=f"nav_{_key}",
                use_container_width=True,
                type="primary" if _is_active else "secondary",
            ):
                if not _is_active:
                    st.session_state.active_module = _key
                    st.rerun()
        else:
            st.button(
                _display,
                key=f"nav_{_key}",
                use_container_width=True,
                disabled=True,
            )

    st.markdown("---")
    _render_sidebar_status()


# ── Route ─────────────────────────────────────────────────────────────────────
_active = st.session_state.get("active_module", "preprocess")

if _active == "upload":
    st.session_state.active_module = "preprocess"
    _active = "preprocess"

if _active == "preprocess":
    from modules.preprocess import render
    render()
elif _active == "forecast":
    from modules.forecast import render
    render()
elif _active == "optimize":
    from modules.optimize import render
    render()
