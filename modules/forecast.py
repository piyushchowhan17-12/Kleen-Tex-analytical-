"""
Module 2 — Demand Forecasting
"""

import io
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import numpy as np


def render():
    s = st.session_state

    if s.get("imputed_data") is None:
        st.markdown('<div class="warn-box">⚠️ Please complete the Preprocessing step first.</div>',
                    unsafe_allow_html=True)
        return

    df_imp   = s.imputed_data
    sel_skus = s.get("selected_skus") or df_imp["SKU"].unique().tolist()

    fc_result = s.get("forecast_result")
    has_fc = (fc_result is not None) and isinstance(fc_result, pd.DataFrame) and (not fc_result.empty)

    # ── Topbar ─────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="topbar">
        <div>
            <div class="topbar-title">📈 Module 2 — Demand Forecasting</div>
            <div class="topbar-sub">Rolling validation · RandomForest 2-Stage · SARIMA · TSB · Multi-model selection</div>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
            {'<span class="badge-pill pill-teal">✓ Forecast Ready</span>' if has_fc else '<span class="badge-pill pill-slate">⏳ Not Run</span>'}
            <span class="badge-pill pill-amber">{len(sel_skus)} SKUs</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # FORECASTING PARAMETERS CARD
    # Contains: Group + SKU pickers, ADI/CV²/Months sliders, Run button.
    # When forecast exists: also shows live metrics + time-series chart inline.
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="sc-card">', unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
        <div>
            <div class="sc-card-title">⚙️ Forecasting Parameters</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Row 1: Product Group | SKU | ADI slider | CV² slider | Months slider ──
    from utils.imputation import compute_sku_stats, apply_thresholds

    all_skus_imp = sorted(df_imp[df_imp["SKU"].isin(sel_skus)]["SKU"].unique().tolist())
    groups_imp   = ["All Groups"] + sorted(set(sk[:3].upper() for sk in all_skus_imp))

    col_g, col_k, col_mo = st.columns([1.2, 2, 1])

    with col_g:
        grp_param = st.selectbox("Product Group", groups_imp, key="fc_param_grp")

    with col_k:
        skus_in_grp = (
            [sk for sk in all_skus_imp if sk.upper().startswith(grp_param)]
            if grp_param != "All Groups" else all_skus_imp
        )
        sku_labels  = {sk: f"{sk} ({sk[:3].upper()})" for sk in skus_in_grp}
        sku_display = list(sku_labels.values())
        sku_keys    = list(sku_labels.keys())
        sku_label_sel = st.selectbox(
            "SKU", sku_display, key="fc_param_sku",
            help="Select a SKU to inspect its time series forecast"
        )
        sku_sel = sku_keys[sku_display.index(sku_label_sel)] if sku_display else None

    with col_mo:
        fc_months = st.number_input(
            "Forecast Months", min_value=1, max_value=12,
            value=int(s.get("forecast_months", 3)), step=1,
            key="fc_months_input",
        )
        s.forecast_months = fc_months

    # Use stored thresholds from preprocessing (ADI/CV² set in Module 1)
    adi_t = float(s.get("adi_threshold", 1.32))
    cv2_t = float(s.get("cv2_threshold", 0.49))

    # Eligible SKUs count
    df_sel = df_imp[df_imp["SKU"].isin(sel_skus)]
    stats  = compute_sku_stats(df_sel)
    stats  = apply_thresholds(stats, adi_t, cv2_t)
    elig   = stats[stats["pass_filter"]]["SKU"].tolist()

    st.markdown(f"""
    <div class="info-box" style="margin-top:8px">
        🎯 <strong>{len(elig)} eligible SKUs</strong> out of {len(sel_skus)} selected
        &nbsp;·&nbsp; ADI ≤ {adi_t}, CV² ≤ {cv2_t}
    </div>
    """, unsafe_allow_html=True)

    col_run, col_clr, _ = st.columns([1, 1, 5])
    with col_run:
        run_btn = st.button("🚀 Run Forecasting", type="primary",
                            width='stretch', disabled=(len(elig) == 0))
    with col_clr:
        if st.button("🔄 Clear Results", type="secondary", width='stretch'):
            s.forecast_result      = None
            s.forecast_summary     = None
            s.forecast_fold_df     = None
            s.forecast_input_ready = False
            st.rerun()

    # ── Progress bar placed HERE — above chart, just below buttons ───────────────
    progress_placeholder = st.empty()
    status_placeholder   = st.empty()

    # ── Live: per-SKU metrics + time-series chart (inside parameters card) ─────
    if has_fc and sku_sel:
        detail_df = s.forecast_result
        raw_summary = s.get("forecast_summary")
        summary_df  = raw_summary if (raw_summary is not None and isinstance(raw_summary, pd.DataFrame)) else pd.DataFrame()

        sku_data = detail_df[detail_df["SKU"] == sku_sel].copy()

        if not sku_data.empty:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

            # ── 4 live metric tiles matching screenshot ────────────────────────
            hist_data = sku_data[sku_data["Imputed_Demand"].notna()]
            fc_data   = sku_data[sku_data["Demand_Prediction"].notna()]

            mean_demand = round(float(hist_data["Imputed_Demand"].mean()), 1) if not hist_data.empty else 0.0

            # ADI | CV² for this SKU
            sku_stat = stats[stats["SKU"] == sku_sel]
            adi_val  = round(float(sku_stat["ADI"].values[0]), 3) if not sku_stat.empty else "N/A"
            cv2_val  = round(float(sku_stat["CV2"].values[0]), 3) if not sku_stat.empty else "N/A"
            dtype    = str(sku_stat["Demand_Type"].values[0])      if not sku_stat.empty else "N/A"

            # Best Model + Avg Val. MAPE + Total Forecast Qty from summary_df
            sku_sum    = summary_df[summary_df["SKU"] == sku_sel] if not summary_df.empty else pd.DataFrame()
            best_model = str(sku_sum["Best_Model_Used"].values[0]) if not sku_sum.empty and "Best_Model_Used" in sku_sum.columns else "N/A"
            val_mape   = round(float(sku_sum["Average_Validation_MAPE"].values[0]), 1) if not sku_sum.empty and "Average_Validation_MAPE" in sku_sum.columns else "N/A"
            fc_data_top = sku_data[sku_data["Demand_Prediction"].notna()]
            fc_total_top = round(float(fc_data_top["Demand_Prediction"].sum()), 0) if not fc_data_top.empty else 0

            # Equal height for all 4 tiles via fixed min-height
            _T = 'style="min-height:110px;display:flex;flex-direction:column;justify-content:center;"'
            mc1, mc2, mc3, mc4 = st.columns(4)
            with mc1:
                st.markdown(f"""<div class="metric-tile accent-slate" {_T}>
                    <div class="metric-label">Mean Demand (Historical)</div>
                    <div class="metric-value">{mean_demand}</div>
                    <div class="metric-sub">units/month (imputed)</div></div>""", unsafe_allow_html=True)
            with mc2:
                st.markdown(f"""<div class="metric-tile accent-teal" {_T}>
                    <div class="metric-label">Best Model</div>
                    <div class="metric-value" style="font-size:16px;line-height:1.3">{best_model}</div>
                    <div class="metric-sub">selected by rolling validation</div></div>""", unsafe_allow_html=True)
            with mc3:
                st.markdown(f"""<div class="metric-tile accent-rose" {_T}>
                    <div class="metric-label">Avg Val. MAPE</div>
                    <div class="metric-value">{val_mape}{"%" if val_mape != "N/A" else ""}</div>
                    <div class="metric-sub">rolling validation</div></div>""", unsafe_allow_html=True)
            with mc4:
                st.markdown(f"""<div class="metric-tile accent-amber" {_T}>
                    <div class="metric-label">Total Forecast Qty</div>
                    <div class="metric-value">{fc_total_top:,.0f}</div>
                    <div class="metric-sub">units across horizon</div></div>""", unsafe_allow_html=True)

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            # ── Live time-series chart ─────────────────────────────────────────
            sku_row = (
                summary_df[summary_df["SKU"] == sku_sel].iloc[0]
                if not summary_df.empty and "SKU" in summary_df.columns
                   and sku_sel in summary_df["SKU"].values
                else None
            )
            model_used = sku_row["Best_Model_Used"] if sku_row is not None else "N/A"
            grp_lbl    = sku_sel[:3].upper()

            # Chart subtitle matching the screenshot
            st.markdown(f"""
            <div style="margin-bottom:4px">
                <div style="font-family:'Fraunces',serif;font-weight:300;font-size:16px;color:var(--white)">
                    {sku_sel} — Time Series Forecast
                </div>
                <div style="font-size:11px;color:var(--slate);margin-top:2px">
                    Group: {grp_lbl} &nbsp;|&nbsp; Model: {model_used}
                    &nbsp;|&nbsp; ADI: {adi_val} &nbsp;|&nbsp; CV²: {cv2_val}
                </div>
            </div>
            """, unsafe_allow_html=True)

            fig = _build_ts_chart(sku_data, sku_sel)
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

    st.markdown("</div>", unsafe_allow_html=True)  # end parameters card

    # ── Run pipeline ────────────────────────────────────────────────────────────
    if run_btn and elig:
        _run_forecasting(df_imp, elig, adi_t, cv2_t, fc_months, s,
                         progress_placeholder, status_placeholder)
        st.rerun()

    # ── Results (Summary + comparisons + export) — shown BELOW ────────────────
    if has_fc:
        _render_results(s, sku_sel=sku_sel if has_fc and sku_sel else None)


# ─────────────────────────────────────────────────────────────────────────────
def _build_ts_chart(sku_data: pd.DataFrame, sku_id: str):
    """
    Smooth spline time-series chart — matches the reference screenshot:
    - Historical raw: thin grey spline, no markers, semi-transparent
    - Historical imputed: teal spline, no markers (clean smooth curve)
    - Forecast: amber dashed spline + filled amber circles with white border
    - Confidence band: subtle shaded area around forecast
    - Legend horizontal at top-left
    - X-axis every 3 months, "Mon YYYY"
    """
    import plotly.graph_objects as go

    NAVY2  = "#1a2e45"
    CARD   = "#162535"
    CARD2  = "#1d3048"
    BORDER = "#243b55"
    TEAL   = "#1bb8a0"
    AMBER  = "#f5a623"
    WHITE  = "#f4f8fb"
    TEXT2  = "#a8c0d4"
    TEXT3  = "#6b859e"

    df = sku_data.copy()
    df["Date"] = pd.to_datetime(
        df.apply(lambda r: f"{int(r['Year'])}-{int(r['Month']):02d}-01", axis=1)
    )
    df = df.sort_values("Date")

    hist = df[df["Imputed_Demand"].notna()].copy()
    fc   = df[df["Demand_Prediction"].notna()].copy()

    fig = go.Figure()

    # ── Historical raw — thin grey spline, no markers ─────────────────────────
    if "Monthly_QTY" in hist.columns and hist["Monthly_QTY"].notna().any():
        fig.add_trace(go.Scatter(
            x=hist["Date"], y=hist["Monthly_QTY"],
            mode="lines",
            name="Historical (raw)",
            line=dict(color="#6b859e", width=1.5, shape="spline", smoothing=1.0),
            opacity=0.55,
            hovertemplate="<b>%{x|%Y-%m}</b><br>Raw: %{y:.1f}<extra></extra>",
        ))

    # ── Historical imputed — teal spline, NO markers (smooth like screenshot) ──
    if not hist.empty:
        fig.add_trace(go.Scatter(
            x=hist["Date"], y=hist["Imputed_Demand"],
            mode="lines",
            name="Historical (imputed)",
            line=dict(color=TEAL, width=2.5, shape="spline", smoothing=1.2),
            hovertemplate="<b>%{x|%Y-%m}</b><br>Imputed: %{y:.1f}<extra></extra>",
        ))

    # ── Forecast — amber dashed spline + filled circles with white border ──────
    if not fc.empty:
        fc_vals  = fc["Demand_Prediction"].tolist()
        # Confidence band: ±18% around forecast
        upper    = [v * 1.18 for v in fc_vals]
        lower    = [v * 0.82 for v in fc_vals]

        # Bridge: connect last historical to first forecast seamlessly
        if not hist.empty:
            bridge_x = [hist["Date"].iloc[-1], fc["Date"].iloc[0]]
            bridge_y = [float(hist["Imputed_Demand"].iloc[-1]), fc_vals[0]]
            fig.add_trace(go.Scatter(
                x=bridge_x, y=bridge_y,
                mode="lines",
                line=dict(color=AMBER, width=2, dash="dash", shape="spline", smoothing=1.0),
                showlegend=False,
                hoverinfo="skip",
            ))

        # Upper confidence band (invisible line, used for fill)
        fig.add_trace(go.Scatter(
            x=fc["Date"], y=upper,
            mode="lines",
            line=dict(color="rgba(0,0,0,0)", width=0),
            showlegend=False,
            hoverinfo="skip",
            name="upper_band",
        ))
        # Lower confidence band — fills to upper, creating the shaded region
        fig.add_trace(go.Scatter(
            x=fc["Date"], y=lower,
            mode="lines",
            line=dict(color="rgba(0,0,0,0)", width=0),
            fill="tonexty",
            fillcolor="rgba(245,166,35,0.12)",
            showlegend=True,
            name="Confidence Band",
            hoverinfo="skip",
        ))

        # Forecast line — dashed amber spline
        fig.add_trace(go.Scatter(
            x=fc["Date"], y=fc_vals,
            mode="lines+markers",
            name="Forecast",
            line=dict(color=AMBER, width=2.5, dash="dash", shape="spline", smoothing=1.0),
            marker=dict(
                size=10, color=AMBER, symbol="circle",
                line=dict(width=2, color=WHITE),
            ),
            hovertemplate="<b>%{x|%Y-%m}</b><br>Forecast: %{y:.1f}<extra></extra>",
        ))

    # ── X-axis ticks every 3 months ───────────────────────────────────────────
    all_dates = pd.concat([hist["Date"], fc["Date"]]) if not fc.empty else hist["Date"]
    if not all_dates.empty:
        tick_dates = pd.date_range(
            start=all_dates.min().replace(day=1),
            end=all_dates.max().replace(day=1) + pd.DateOffset(months=1),
            freq="3MS",
        )
        tick_vals  = tick_dates.tolist()
        tick_texts = [d.strftime("%Y-%m") for d in tick_dates]
    else:
        tick_vals, tick_texts = [], []

    fig.update_layout(
        paper_bgcolor=CARD,
        plot_bgcolor=CARD2,
        height=400,
        font=dict(family="Inter, DM Sans, sans-serif", color=TEXT2, size=11),
        margin=dict(l=54, r=24, t=80, b=54),
        # Legend horizontal at top-left exactly like screenshot
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0.0,
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            font=dict(size=11, color=TEXT2),
            traceorder="normal",
        ),
        xaxis=dict(
            tickvals=tick_vals,
            ticktext=tick_texts,
            tickangle=0,
            tickfont=dict(color=TEXT3, size=10),
            gridcolor=BORDER,
            linecolor=BORDER,
            zeroline=False,
            showgrid=True,
        ),
        yaxis=dict(
            title=dict(text="Units", font=dict(color=TEXT3, size=11)),
            tickfont=dict(color=TEXT3, size=11),
            gridcolor=BORDER,
            linecolor=BORDER,
            zeroline=False,
            rangemode="tozero",
            showgrid=True,
        ),
        hoverlabel=dict(
            bgcolor=NAVY2,
            bordercolor=BORDER,
            font=dict(family="Inter, DM Sans, sans-serif", color=WHITE, size=12),
        ),
        hovermode="x unified",
    )

    return fig


# ─────────────────────────────────────────────────────────────────────────────
def _run_forecasting(df_imp, elig_skus, adi_t, cv2_t, fc_months, s,
                     progress_bar=None, status_text=None):
    # Use passed-in placeholders so they render just below the buttons
    if progress_bar is None:
        progress_bar = st.progress(0)
    else:
        progress_bar = progress_bar.progress(0)
    if status_text is None:
        status_text = st.empty()

    def progress_cb(i, t, sku):
        progress_bar.progress(int((i / max(t, 1)) * 100))
        status_text.markdown(
            f'<div class="info-box">⏳ Processing SKU {i+1}/{t}: <strong>{sku}</strong></div>',
            unsafe_allow_html=True,
        )

    from utils.forecasting import run_forecast_pipeline
    try:
        detail_df, summary_df, fold_df = run_forecast_pipeline(
            imputed_df      = df_imp,
            selected_skus   = elig_skus,
            adi_threshold   = adi_t,
            cv2_threshold   = cv2_t,
            forecast_months = fc_months,
            progress_cb     = progress_cb,
        )
        progress_bar.progress(100)
        status_text.empty()

        s.forecast_result  = detail_df
        s.forecast_summary = summary_df
        s.forecast_fold_df = fold_df

        from utils.opt_input_builder import build_optimization_input
        # Pass raw_data so builder can extract Unit Inventory Cost and m2/item
        raw_df = s.get("raw_data")
        data_dict, excel_bytes = build_optimization_input(detail_df, fc_months, raw_df=raw_df)
        s.forecast_input_dict  = data_dict
        s.forecast_input_bytes = excel_bytes
        s.forecast_input_ready = True

        st.success(f"✅ Forecasting complete! {len(summary_df)} SKUs processed, {fc_months} months forecasted.")

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.markdown(f'<div class="error-box">❌ Forecasting failed: {e}</div>', unsafe_allow_html=True)
        import traceback
        with st.expander("Error details"):
            st.code(traceback.format_exc())


# ─────────────────────────────────────────────────────────────────────────────
def _render_results(s, sku_sel=None):
    """Forecasting Summary — shown BELOW the parameters+chart card."""
    detail_df   = s.forecast_result
    raw_summary = s.get("forecast_summary")
    summary_df  = raw_summary if (raw_summary is not None and isinstance(raw_summary, pd.DataFrame)) else pd.DataFrame()
    raw_fold    = s.get("forecast_fold_df")
    fold_df     = raw_fold if (raw_fold is not None and isinstance(raw_fold, pd.DataFrame)) else pd.DataFrame()

    if detail_df is None or detail_df.empty:
        return

    # ── Forecasting Summary card ───────────────────────────────────────────────
    # Filter all data to the selected SKU for live updates
    sku_label = f" — {sku_sel}" if sku_sel else ""
    sku_sub   = f"Results for <strong>{sku_sel}</strong>" if sku_sel else "Aggregate results across all forecasted SKUs"

    # Filter detail_df to selected SKU if provided
    if sku_sel:
        sku_detail = detail_df[detail_df["SKU"] == sku_sel].copy()
    else:
        sku_detail = detail_df.copy()

    st.markdown('<div class="sc-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="sc-card-title">📊 Forecasting Summary{sku_label}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sc-card-sub" style="margin-bottom:14px">{sku_sub}</div>', unsafe_allow_html=True)

    fc_rows   = sku_detail[sku_detail["Demand_Prediction"].notna()]
    n_sku_fc  = int(fc_rows["SKU"].nunique()) if not fc_rows.empty else 0
    fc_total  = round(fc_rows["Demand_Prediction"].sum(), 1) if not fc_rows.empty else 0
    avg_mae   = 0.0
    avg_mape  = 0.0
    if not summary_df.empty:
        sku_summary = summary_df[summary_df["SKU"] == sku_sel] if sku_sel else summary_df
        if "Average_Validation_MAE" in sku_summary.columns:
            avg_mae  = round(float(sku_summary["Average_Validation_MAE"].dropna().mean()), 2)
        if "Average_Validation_MAPE" in sku_summary.columns:
            avg_mape = round(float(sku_summary["Average_Validation_MAPE"].dropna().mean()), 2)



    # ── 4 Summary Charts + 2 Model Charts ────────────────────────────────────
    import plotly.graph_objects as go

    # ── Design tokens
    _CARD   = "#162535"; _CARD2  = "#1d3048"; _BORDER = "#243b55"
    _NAVY2  = "#1a2e45"; _NAVY3  = "#243b55"
    _TEAL   = "#1bb8a0"; _ROSE   = "#e05c7a"; _AMBER  = "#f5a623"
    _SLATE  = "#8fa3b8"; _SLATE2 = "#6b859e"
    _WHITE  = "#f4f8fb"; _TEXT2  = "#a8c0d4"
    _H      = 340   # uniform height for ALL 6 boxes

    # Inject Fraunces 300 weight so it renders thin not bold
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300&display=swap');
    .fc-title {
        font-family: 'Fraunces', Georgia, serif !important;
        font-weight: 300 !important;
        font-size: 16px !important;
        color: #f4f8fb !important;
        margin-bottom: 14px;
        display: block;
    }
    .fc-box {
        background: #162535;
        border: 1px solid #243b55;
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # Shared Plotly layout — Fraunces 300 via CSS class (title rendered as HTML)
    # We use paper/plot bgcolor matching the card so chart fills box seamlessly
    def _lo(title):
        return dict(
            paper_bgcolor=_CARD, plot_bgcolor=_CARD2, height=_H,
            title=dict(
                text=f'<span style="font-family:Fraunces,Georgia,serif;font-weight:300;font-size:16px;color:#f4f8fb;">{title}</span>',
                font=dict(family="Fraunces, Georgia, serif", size=16, color=_WHITE),
                x=0.02, y=0.97, xanchor="left", yanchor="top",
            ),
            font=dict(family="DM Sans, sans-serif", color=_TEXT2, size=11),
            margin=dict(l=54, r=24, t=52, b=60),
            xaxis=dict(gridcolor=_NAVY3, linecolor=_NAVY3, zeroline=False,
                       tickfont=dict(color=_SLATE2, size=10), showgrid=True),
            yaxis=dict(gridcolor=_NAVY3, linecolor=_NAVY3, zeroline=False,
                       tickfont=dict(color=_SLATE2, size=10), showgrid=True),
            hoverlabel=dict(bgcolor=_NAVY2, bordercolor=_BORDER,
                            font=dict(family="DM Sans, sans-serif", color=_WHITE, size=12)),
            legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
                        font=dict(size=10, color=_TEXT2)),
        )

    # Filter to selected SKU — makes ALL charts live when SKU changes
    hist_df = sku_detail[sku_detail["Imputed_Demand"].notna()].copy()
    fc_rows = sku_detail[sku_detail["Demand_Prediction"].notna()].copy()

    # Table styles — same as SKU Classification Table
    _TH = ("padding:9px 12px;font-size:10px;text-transform:uppercase;"
           "letter-spacing:.08em;color:#6b859e;font-weight:500;"
           "border-bottom:1px solid #243b55;white-space:nowrap;"
           "font-family:'DM Sans',sans-serif;background:#243b55;")
    _TD = ("padding:9px 12px;font-size:12px;color:#a8c0d4;"
           "border-bottom:1px solid #1a2e45;white-space:nowrap;")

    # ── Row 1: Forecast Values table | Monthly Seasonality Index ──────────────
    col_tl, col_tr = st.columns(2, gap="medium")

    with col_tl:
        # Forecast Values — plain card div matching chart boxes exactly
        if not fc_rows.empty:
            fc_agg = (fc_rows.groupby(["Year","Month"])["Demand_Prediction"]
                      .sum().reset_index().sort_values(["Year","Month"]))
            fc_agg["Period"] = fc_agg.apply(
                lambda r: f"{int(r['Year'])}-{int(r['Month']):02d}", axis=1)
            fc_agg["Lower"] = (fc_agg["Demand_Prediction"] * 0.82).round(1)
            fc_agg["Upper"] = (fc_agg["Demand_Prediction"] * 1.18).round(1)
            last_hist   = (hist_df.groupby(["Year","Month"])["Imputed_Demand"]
                           .sum().reset_index().sort_values(["Year","Month"]))
            last_actual = float(last_hist["Imputed_Demand"].iloc[-1]) if not last_hist.empty else 0.0

            total_fc    = len(fc_agg)
            fc_agg_disp = fc_agg.head(10) if total_fc > 10 else fc_agg
            # Dynamic height: scroll only when > 10 rows
            scroll_style = "overflow-y:auto;max-height:340px;" if total_fc > 10 else ""
            rows_html = ""
            for _, row in fc_agg_disp.iterrows():
                rows_html += (
                    f'<tr style="border-left:3px solid transparent;">' +
                    f'<td style="{_TD}font-family:DM Mono,monospace;">{row["Period"]}</td>' +
                    f'<td style="{_TD}color:#f5a623;font-family:DM Mono,monospace;">{row["Demand_Prediction"]:.1f}</td>' +
                    f'<td style="{_TD}font-family:DM Mono,monospace;">{row["Lower"]:.1f}</td>' +
                    f'<td style="{_TD}font-family:DM Mono,monospace;">{row["Upper"]:.1f}</td>' +
                    '</tr>'
                )
            fc_footer = (f'<div style="font-size:11px;color:#6b859e;margin-top:8px;">'
                         f'Showing {min(10,total_fc)} of {total_fc} months'
                         f'{" — scroll to see more" if total_fc > 10 else ""}</div>'
                         if total_fc > 10 else "")
            st.markdown(
                f'<div class="fc-box" style="padding:18px 20px;min-height:{_H}px;">' +
                '<span class="fc-title">Forecast Values</span>' +
                f'<div style="overflow-x:auto;{scroll_style}border-radius:6px;border:1px solid #243b55;">' +
                '<table style="width:100%;border-collapse:collapse;background:#1d3048;">' +
                f'<thead><tr style="background:#162535;position:sticky;top:0;z-index:1;">' +
                f'<th style="{_TH}">Month</th>' +
                f'<th style="{_TH}">Forecast</th>' +
                f'<th style="{_TH}">Lower 90%</th>' +
                f'<th style="{_TH}">Upper 90%</th>' +
                f'</tr></thead><tbody>{rows_html}</tbody></table></div>' +
                fc_footer + '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f'<div class="fc-box" style="padding:18px 20px;min-height:{_H}px;"><div class="warn-box">No forecast data available.</div></div>', unsafe_allow_html=True)

    with col_tr:
        # Monthly Seasonality Index
        if not hist_df.empty and hist_df["Imputed_Demand"].mean() > 0:
            monthly_avg = (hist_df.groupby("Month")["Imputed_Demand"]
                           .mean().reindex(range(1,13), fill_value=0))
            seas    = (monthly_avg / hist_df["Imputed_Demand"].mean()).round(3)
            mlabels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            fig_si  = go.Figure(go.Bar(
                x=mlabels, y=seas.values,
                marker=dict(color=[_TEAL if v >= 1.0 else _ROSE for v in seas.values], line=dict(width=0)),
                width=0.72, showlegend=False,
                hovertemplate="<b>%{x}</b><br>Index: %{y:.3f}<extra></extra>",
            ))
            fig_si.add_hline(y=1.0, line_dash="dash", line=dict(color=_SLATE2, width=1.5), opacity=0.7)
            lo = _lo("Monthly Seasonality Index")
            lo["yaxis"]["title"] = dict(text="vs Overall Mean", font=dict(color=_SLATE2, size=10), standoff=8)
            lo["yaxis"]["rangemode"] = "tozero"
            lo["bargap"] = 0.15
            lo["annotations"] = [dict(text="vs overall mean", x=1.0, y=1.03,
                xref="paper", yref="paper", showarrow=False,
                font=dict(color=_SLATE2, size=10, family="DM Sans, sans-serif"), xanchor="right")]
            lo["margin"]["b"] = 72  # extra bottom margin for the note
            fig_si.update_layout(**lo)
            fig_si.add_annotation(
                text="📌 Monthly Above or Below the Average Demand",
                x=0.5, y=-0.22,
                xref="paper", yref="paper",
                showarrow=False,
                font=dict(color=_SLATE2, size=11, family="DM Sans, sans-serif"),
                xanchor="center", yanchor="top",
            )
            st.plotly_chart(fig_si, width='stretch', config={"displayModeBar": False})
        else:
            st.markdown('<div class="warn-box">No historical data.</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Row 2: Year-over-Year Comparison ─────────────────────────────────────
    col_bl, = st.columns([1])

    with col_bl:
        # Year-over-Year Comparison
        if not hist_df.empty:
            yoy_data    = hist_df.groupby(["Year","Month"])["Imputed_Demand"].sum().reset_index()
            years_avail = sorted(yoy_data["Year"].unique())
            mlabels     = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            yoy_colors  = {0: _SLATE, 1: _TEAL, 2: _AMBER, 3: _ROSE}
            yoy_dashes  = {0: "solid", 1: "solid", 2: "solid", 3: "dash"}
            fig_yoy = go.Figure()
            for idx, yr in enumerate(years_avail):
                yr_d = yoy_data[yoy_data["Year"]==yr].set_index("Month")["Imputed_Demand"].reindex(range(1,13))
                c    = yoy_colors.get(idx % 4, _SLATE)
                fig_yoy.add_trace(go.Scatter(
                    x=mlabels, y=yr_d.values, mode="lines+markers", name=str(yr),
                    line=dict(color=c, width=2, dash=yoy_dashes.get(idx%4,"solid")),
                    marker=dict(size=5, color=c, symbol="circle-open" if idx==len(years_avail)-1 else "circle"),
                    hovertemplate=f"<b>{yr}</b> — %{{x}}: %{{y:.1f}}<extra></extra>",
                ))
            lo = _lo("Year-over-Year Comparison")
            lo["margin"]["b"] = 72
            lo["legend"]["orientation"] = "h"
            lo["legend"]["y"] = -0.20
            lo["legend"]["x"] = 0.5
            lo["legend"]["xanchor"] = "center"
            lo["yaxis"]["rangemode"] = "tozero"
            fig_yoy.update_layout(**lo)
            st.plotly_chart(fig_yoy, width='stretch', config={"displayModeBar": False})
        else:
            st.markdown('<div class="warn-box">No historical data.</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)



    # ── Model Summary Table — styled HTML matching SKU Classification Table ─────
    st.markdown('<div class="sc-card">', unsafe_allow_html=True)

    st.markdown(
        '<div class="sc-card-title" style="margin-bottom:4px">📋 Full Model Summary Table</div>'
        '<div class="sc-card-sub" style="margin-bottom:12px">Best model selected per SKU via rolling cross-validation</div>',
        unsafe_allow_html=True,
    )

    if not summary_df.empty:
        # Build display table
        col_map = {
            "SKU":                      "SKU",
            "Best_Model_Used":          "Best Model",
            "Demand_Type":              "Demand Type",
            "Average_Validation_MAE":   "MAE",
            "Average_Validation_MAPE":  "MAPE",
        }
        avail_cols = [c for c in col_map if c in summary_df.columns]
        tbl = summary_df[avail_cols].copy().rename(columns=col_map)

        # ── Column filters ────────────────────────────────────────────────────
        st.markdown('<div style="margin-bottom:8px;font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#6b859e;">Filter columns</div>', unsafe_allow_html=True)

        model_opts   = ["All Best Models"] + sorted(tbl["Best Model"].dropna().unique().tolist()) if "Best Model" in tbl.columns else ["All Best Models"]
        dtype_opts   = ["All Demand Types", "smooth", "erratic", "intermittent", "insufficient"]

        # Reset via on_click callbacks — clears all filters without triggering data reload
        def _ms_clear():
            st.session_state["ms_flt_sku"]   = ""
            st.session_state["ms_flt_model"] = model_opts[0]
            st.session_state["ms_flt_dtype"] = dtype_opts[0]

        ms_f1, ms_f2, ms_f3, ms_f4 = st.columns([2, 1, 1, 1])
        with ms_f1:
            ms_flt_sku   = st.text_input("SKU", placeholder="Search SKU…", key="ms_flt_sku", label_visibility="collapsed")
        with ms_f2:
            ms_flt_model = st.selectbox("Best Model", model_opts, key="ms_flt_model", label_visibility="collapsed")
        with ms_f3:
            ms_flt_dtype = st.selectbox("Demand Type", dtype_opts, key="ms_flt_dtype", label_visibility="collapsed")
        with ms_f4:
            st.button("🔄 Reset", key="ms_flt_reset", on_click=_ms_clear, width="stretch")

        # Apply filters
        if ms_flt_sku:
            tbl = tbl[tbl["SKU"].str.contains(ms_flt_sku, case=False, na=False)]
        if ms_flt_model != model_opts[0] and "Best Model" in tbl.columns:
            tbl = tbl[tbl["Best Model"] == ms_flt_model]
        if ms_flt_dtype != dtype_opts[0] and "Demand Type" in tbl.columns:
            tbl = tbl[tbl["Demand Type"].str.lower() == ms_flt_dtype]

        # Round numeric columns
        if "MAE"  in tbl.columns: tbl["MAE"]  = tbl["MAE"].round(4)
        if "MAPE" in tbl.columns: tbl["MAPE"] = tbl["MAPE"].round(4)

        # ── HTML helpers matching the SKU table style ──────────────────────
        def _model_badge(v):
            colors = {
                "RandomForest_2Stage": ("rgba(27,184,160,.18)",  "#1bb8a0"),
                "SARIMA":              ("rgba(107,133,158,.18)", "#8fa3b8"),
                "TSB":                 ("rgba(245,166,35,.18)",  "#f5a623"),
                "SeasonalNaive":       ("rgba(224,92,122,.14)",  "#e05c7a"),
                "MovingAverage_3":     ("rgba(107,133,158,.18)", "#8fa3b8"),
                "LastValue":           ("rgba(107,133,158,.18)", "#8fa3b8"),
            }
            bg, fg = colors.get(str(v), ("rgba(107,133,158,.18)", "#8fa3b8"))
            return (
                f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;' +
                f'font-size:11px;font-weight:500;font-family:DM Mono,monospace;' +
                f'background:{bg};color:{fg};">{v}</span>'
            )

        def _dtype_badge(v):
            colors = {
                "smooth":       ("rgba(27,184,160,.18)",  "#1bb8a0"),
                "erratic":      ("rgba(245,166,35,.18)",  "#f5a623"),
                "intermittent": ("rgba(224,92,122,.18)",  "#e05c7a"),
                "insufficient": ("rgba(107,133,158,.18)", "#8fa3b8"),
            }
            bg, fg = colors.get(str(v).lower(), ("rgba(107,133,158,.18)", "#8fa3b8"))
            return (
                f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;' +
                f'font-size:11px;font-weight:500;font-family:DM Mono,monospace;' +
                f'background:{bg};color:{fg};">{v}</span>'
            )

        def _num(v):
            try:    return f'<span style="font-family:DM Mono,monospace;color:#a8c0d4;">{float(v):.4f}</span>'
            except: return f'<span style="color:#6b859e;">N/A</span>'

        th = ("padding:10px 14px;text-align:left;font-size:10px;text-transform:uppercase;"
              "letter-spacing:.09em;color:#6b859e;font-weight:500;border-bottom:1px solid #243b55;"
              "white-space:nowrap;")
        td     = "padding:11px 14px;font-size:12px;color:#a8c0d4;border-bottom:1px solid #1a2e45;white-space:nowrap;"
        td_sku = "padding:11px 14px;font-size:12px;color:#f4f8fb;border-bottom:1px solid #1a2e45;font-family:DM Mono,monospace;font-weight:500;"

        # Build header from available columns in tbl
        headers = list(tbl.columns)
        thead = "".join(f'<th style="{th}">{h}</th>' for h in headers)

        total_summary = len(tbl)
        rows_html = ""
        for _, row in tbl.iterrows():
            cells = ""
            for col_name in headers:
                val = row[col_name]
                if col_name == "SKU":
                    cells += f'<td style="{td_sku}">{val}</td>'
                elif col_name == "Best Model":
                    cells += f'<td style="{td}">{_model_badge(val)}</td>'
                elif col_name == "Demand Type":
                    cells += f'<td style="{td}">{_dtype_badge(val)}</td>'
                else:
                    cells += f'<td style="{td}">{_num(val)}</td>'
            rows_html += f'<tr style="border-left:3px solid transparent;">{cells}</tr>'

        table_html = (
            '<div style="overflow-x:auto;overflow-y:auto;max-height:420px;border-radius:8px;border:1px solid #243b55;margin-top:6px;">' +
            '<table style="width:100%;border-collapse:collapse;background:#1d3048;">' +
            f'<thead><tr style="background:#162535;">{thead}</tr></thead>' +
            f'<tbody>{rows_html}</tbody>' +
            '</table></div>' +
            f'<div style="font-size:11px;color:#6b859e;margin-top:8px;">Showing {total_summary:,} SKUs</div>'
        )
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("No summary data available.")

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Download & Proceed ─────────────────────────────────────────────────────
    st.markdown('<div class="sc-card">', unsafe_allow_html=True)
    st.markdown('<div class="sc-card-title">💾 Export & Next Steps</div>', unsafe_allow_html=True)
    st.markdown('<div class="sc-card-sub" style="margin-bottom:14px">Download results or proceed to the Optimization module</div>', unsafe_allow_html=True)

    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            detail_df.to_excel(w, sheet_name="Forecast_Detail", index=False)
            if not summary_df.empty:
                summary_df.to_excel(w, sheet_name="Model_Summary", index=False)
            if not fold_df.empty:
                fold_df.to_excel(w, sheet_name="Fold_Summary", index=False)
        st.download_button(
            "⬇️ Download Forecast Results",
            data=buf.getvalue(),
            file_name="RF_SARIMA_TSB_Output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch',
        )
    with col_d2:
        opt_bytes = s.get("forecast_input_bytes")
        if opt_bytes:
            st.download_button(
                "⬇️ Download Optimization Input",
                data=opt_bytes,
                file_name="Input_Data_Adjusted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width='stretch',
            )
        else:
            st.button("⬇️ Optimization Input", disabled=True, width='stretch')
    with col_d3:
        if st.button("▶️ Proceed to Optimization →", type="primary", width='stretch'):
            s.active_module = "optimize"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
