"""
Module 1 — Data Preprocessing & Imputation
Merged from upload.py + preprocess.py.
Handles: file upload → SKU selection → imputation → ADI/CV² classification.
No logic changes — only UI flow merged into one module.
"""

import io
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import numpy as np


def render():
    s = st.session_state

    # ════════════════════════════════════════════════════════════════════════
    # SECTION A — File Upload & SKU Selection (was upload.py)
    # Shows until data is confirmed; collapses to a summary banner after.
    # ════════════════════════════════════════════════════════════════════════

    if s.get("raw_data") is None:
        _render_upload_section()
        return  # nothing more to show until data is loaded


    # ── Data already loaded — show compact banner with option to re-upload ──
    df_loaded  = s.raw_data
    n_rows     = len(df_loaded)
    n_skus_raw = df_loaded["SKU"].nunique()
    filename   = s.get("raw_filename", "file.xlsx")

    # Topbar (imputation state)
    sel_sku = s.get("selected_skus") or df_loaded["SKU"].unique().tolist()

    # Run imputation (or use cached)
    if s.get("imputed_data") is None:
        with st.spinner("Running imputation pipeline…"):
            from utils.imputation import impute_demand
            df_imp = impute_demand(df_loaded[df_loaded["SKU"].isin(sel_sku)].copy())
            s.imputed_data = df_imp
    else:
        df_imp = s.imputed_data

    from utils.imputation import compute_sku_stats, apply_thresholds, get_imputation_summary
    stats_df = compute_sku_stats(df_imp)
    adi_t    = s.get("adi_threshold", 1.32)
    cv2_t    = s.get("cv2_threshold", 0.49)
    stats_df = apply_thresholds(stats_df, adi_t, cv2_t)
    summary  = get_imputation_summary(df_loaded[df_loaded["SKU"].isin(sel_sku)].copy(), df_imp)
    n_pass   = int(stats_df["pass_filter"].sum())

    st.markdown(f"""
    <div class="topbar">
        <div>
            <div class="topbar-title">Module 1 — Data Preprocessing &amp; Imputation</div>
        </div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <span class="badge-pill pill-teal">✓ Imputation Applied</span>
            <span class="badge-pill pill-amber">{len(sel_sku)} SKUs Loaded</span>
            <span class="badge-pill pill-teal">{n_pass} Pass Filter</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION B — Data source banner (compact, no expander)
    # ════════════════════════════════════════════════════════════════════════
    st.markdown(
        f'<div class="info-box" style="margin-bottom:12px;">'
        f'<strong>{filename}</strong> — {n_rows:,} rows · {n_skus_raw:,} SKUs · {len(sel_sku)} selected'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ════════════════════════════════════════════════════════════════════════
    # SECTION B2 — Re-select SKUs (fixed container, no expander)
    # ════════════════════════════════════════════════════════════════════════
    with st.container(border=True):
        st.markdown(
            '<p style="font-family:Fraunces,Georgia,serif;font-weight:300;'
            'font-size:16px;color:#f4f8fb;margin:0 0 4px 0;">Re-select SKUs</p>',
            unsafe_allow_html=True,
        )
        _render_sku_selection_inline(df_loaded, sel_sku)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        col_reup, _ = st.columns([1, 3])
        with col_reup:
            if st.button("Upload New File", type="secondary", width='stretch', key="reupload_btn"):
                for k in ["raw_data", "raw_filename", "selected_skus", "imputed_data",
                          "forecast_result", "forecast_summary", "forecast_fold_df",
                          "forecast_input_ready", "forecast_input_dict", "forecast_input_bytes",
                          "optimization_result"]:
                    st.session_state[k] = None
                st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION D — Imputation Metrics
    # ════════════════════════════════════════════════════════════════════════
    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        (c1, "Total Rows",       f"{summary['total_rows']:,}",      "observations",       "accent-teal"),
        (c2, "Unique SKUs",      f"{summary['unique_skus']:,}",      "products",           "accent-amber"),
        (c3, "Zero Demand Rows", f"{summary['zero_demand_rows']:,}", "in raw data",        "accent-rose"),
        (c4, "Imputed Rows",     f"{summary['imputed_rows']:,}",     "values corrected",   "accent-teal"),
        (c5, "Imputation Rate",  f"{summary['imputation_pct']}%",    "of zero rows fixed", "accent-amber"),
    ]
    for col, label, val, sub, accent in metrics:
        with col:
            st.markdown(f"""
            <div class="metric-tile {accent}">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{val}</div>
                <div class="metric-sub">{sub}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION E — ADI / CV² Threshold Controls + Charts
    # ════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="sc-card-title">SKU Classification — ADI / CV² Thresholds</div>', unsafe_allow_html=True)

    col_ctrl1, col_ctrl2, col_ctrl3, _ = st.columns([1, 1, 1, 1])
    with col_ctrl1:
        groups    = ["All Groups"] + sorted(stats_df["Group"].unique().tolist())
        group_sel = st.selectbox("Product Group", groups)
    with col_ctrl2:
        adi_t = st.slider(
            "ADI Threshold (≤)", min_value=1.0, max_value=4.0,
            value=float(adi_t), step=0.05, format="%.2f",
            help="ADI = total periods / nonzero periods. Lower = less intermittent.",
        )
        s.adi_threshold = adi_t
    with col_ctrl3:
        cv2_t = st.slider(
            "CV² Threshold (≤)", min_value=0.1, max_value=3.0,
            value=float(cv2_t), step=0.05, format="%.2f",
            help="CV² = (std/mean)² of positive demand values. Lower = more stable.",
        )
        s.cv2_threshold = cv2_t

    stats_df = apply_thresholds(stats_df, adi_t, cv2_t)
    disp_stats = (
        stats_df[stats_df["Group"] == group_sel]
        if group_sel != "All Groups" else stats_df
    )
    n_pass = int(disp_stats["pass_filter"].sum())
    n_fail = len(disp_stats) - n_pass

    from utils.charts import adi_cv2_scatter, demand_type_donut
    col_scat, col_donut = st.columns([3, 2])
    with col_scat:
        fig_scat = adi_cv2_scatter(disp_stats, adi_t, cv2_t, height=300)
        st.plotly_chart(fig_scat, width='stretch', config={"displayModeBar": False})
    with col_donut:
        pass_stats  = disp_stats[disp_stats["pass_filter"]]
        type_counts = pass_stats["Demand_Type"].value_counts().to_dict()
        if type_counts:
            fig_donut = demand_type_donut(type_counts, height=260)
            st.plotly_chart(fig_donut, width='stretch', config={"displayModeBar": False})
        else:
            st.markdown('<div class="warn-box">No SKUs pass current thresholds.</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="info-box">
        ✅ <strong>{n_pass} SKUs pass</strong> both thresholds &nbsp;|&nbsp;
        ❌ <strong>{n_fail} SKUs excluded</strong> &nbsp;|&nbsp;
        These {n_pass} SKUs will proceed to Demand Forecasting
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION F — SKU Classification Table (styled like HTML reference)
    # ════════════════════════════════════════════════════════════════════════

    st.markdown(
        '<div class="sc-card-title" style="margin-bottom:4px">SKU Classification Table</div>',
        unsafe_allow_html=True,
    )

    # ── Column filters ────────────────────────────────────────────────────────
    st.markdown('<div style="margin-bottom:8px;font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#6b859e;">Filter columns</div>', unsafe_allow_html=True)
    f1, f2, f3, f4, f5 = st.columns([2, 1, 1, 1, 1])
    with f1:
        # Reset: clear all filter keys BEFORE widgets are drawn
        grp_opts   = ["All Groups"]       + sorted(disp_stats["Group"].dropna().unique().tolist())
        dtype_opts = ["All Demand Types",   "smooth", "erratic", "intermittent", "insufficient"]
        stat_opts  = ["All Statuses",       "Passing Only", "Excluded Only"]

        if st.session_state.pop("_clf_reset", False):
            st.session_state["clf_flt_sku"]   = ""
            st.session_state["clf_flt_grp"]   = grp_opts[0]
            st.session_state["clf_flt_dtype"] = dtype_opts[0]
            st.session_state["clf_flt_stat"]  = stat_opts[0]

        flt_sku   = st.text_input("SKU", placeholder="Search SKU…", key="clf_flt_sku", label_visibility="collapsed")
    with f2:
        flt_grp   = st.selectbox("Group", grp_opts, key="clf_flt_grp", label_visibility="collapsed")
    with f3:
        flt_dtype = st.selectbox("Demand Type", dtype_opts, key="clf_flt_dtype", label_visibility="collapsed")
    with f4:
        flt_stat  = st.selectbox("Status", stat_opts, key="clf_flt_stat", label_visibility="collapsed")
    with f5:
        if st.button("Reset", key="clf_flt_reset", width="stretch"):
            st.session_state["_clf_reset"] = True
            st.rerun()

    # Apply filters
    tbl_data = disp_stats.copy()
    if flt_sku:
        tbl_data = tbl_data[tbl_data["SKU"].str.contains(flt_sku, case=False, na=False)]
    if flt_grp != grp_opts[0]:
        tbl_data = tbl_data[tbl_data["Group"] == flt_grp]
    if flt_dtype != dtype_opts[0]:
        tbl_data = tbl_data[tbl_data["Demand_Type"].str.lower() == flt_dtype]
    if flt_stat == "Passing Only":
        tbl_data = tbl_data[tbl_data["pass_filter"]]
    elif flt_stat == "Excluded Only":
        tbl_data = tbl_data[~tbl_data["pass_filter"]]

    # Helpers for styled cells
    def _demand_badge(v):
        colors = {
            "smooth":       ("rgba(27,184,160,.18)",  "#1bb8a0"),
            "erratic":      ("rgba(245,166,35,.18)",  "#f5a623"),
            "intermittent": ("rgba(224,92,122,.18)",  "#e05c7a"),
            "insufficient": ("rgba(107,133,158,.18)", "#8fa3b8"),
        }
        bg, fg = colors.get(v, ("rgba(107,133,158,.18)", "#8fa3b8"))
        return (
            f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;' +
            f'font-size:16px;font-weight:500;font-family:DM Mono,monospace;' +
            f'background:{bg};color:{fg};">{v}</span>'
        )

    def _status_badge(passed):
        if passed:
            return (
                '<span style="display:inline-block;padding:2px 12px;border-radius:12px;' +
                'font-size:16px;font-weight:600;font-family:DM Mono,monospace;' +
                'background:rgba(27,184,160,.18);color:#1bb8a0;border:1px solid rgba(27,184,160,.35);">PASS</span>'
            )
        return (
            '<span style="display:inline-block;padding:2px 10px;border-radius:12px;' +
            'font-size:16px;font-weight:600;font-family:DM Mono,monospace;' +
            'background:rgba(224,92,122,.14);color:#e05c7a;border:1px solid rgba(224,92,122,.3);">EXCLUDE</span>'
        )

    def _group_chip(g):
        return (
            f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;' +
            f'font-size:16px;font-family:DM Mono,monospace;background:#243b55;color:#8fa3b8;">{g}</span>'
        )

    def _num_color(v, passed, fmt=".3f"):
        color = "#1bb8a0" if passed else "#e05c7a"
        return f'<span style="color:{color};font-family:DM Mono,monospace;font-weight:500;">{v:{fmt}}</span>'

    th = ("padding:10px 14px;text-align:left;font-size:16px;text-transform:uppercase;"
          "letter-spacing:.09em;color:#6b859e;font-weight:500;border-bottom:1px solid #243b55;"
          "white-space:nowrap;")
    td = "padding:11px 14px;font-size:16px;color:#a8c0d4;border-bottom:1px solid #1a2e45;white-space:nowrap;"
    td_sku = "padding:11px 14px;font-size:16px;color:#f4f8fb;border-bottom:1px solid #1a2e45;font-family:DM Mono,monospace;font-weight:500;"

    total_rows = len(tbl_data)
    rows_html = ""
    for _, row in tbl_data.iterrows():
        passed  = bool(row["pass_filter"])
        bl      = "border-left:3px solid #1bb8a0;" if passed else "border-left:3px solid transparent;"
        bg_base = "rgba(27,184,160,0.04)" if passed else "transparent"
        rows_html += (
            f'<tr style="{bl}background:{bg_base};">' +
            f'<td style="{td_sku}">{row["SKU"]}</td>' +
            f'<td style="{td}">{_group_chip(row["Group"])}</td>' +
            f'<td style="{td}">{_num_color(row["ADI"], passed, ".3f")}</td>' +
            f'<td style="{td}">{_num_color(row["CV2"], passed, ".3f")}</td>' +
            f'<td style="{td}">{int(row["Nonzero_Periods"])}</td>' +
            f'<td style="{td}">{int(row["Total_Periods"])}</td>' +
            f'<td style="{td}">{row["Mean_Demand"]:.1f}</td>' +
            f'<td style="{td}">{_demand_badge(row["Demand_Type"])}</td>' +
            f'<td style="{td}">{_status_badge(passed)}</td>' +
            '</tr>'
        )

    table_html = (
        '<div style="overflow-x:auto;overflow-y:auto;max-height:420px;border-radius:8px;border:1px solid #243b55;margin-top:6px;">' +
        '<table style="width:100%;border-collapse:collapse;background:#1d3048;">' +
        '<thead><tr style="background:#162535;">' +
        f'<th style="{th}">SKU</th>' +
        f'<th style="{th}">Group</th>' +
        f'<th style="{th}">ADI</th>' +
        f'<th style="{th}">CV²</th>' +
        f'<th style="{th}">Nonzero Periods</th>' +
        f'<th style="{th}">Total Periods</th>' +
        f'<th style="{th}">Mean Demand</th>' +
        f'<th style="{th}">Demand Type</th>' +
        f'<th style="{th}">Status</th>' +
        '</tr></thead>' +
        f'<tbody>{rows_html}</tbody>' +
        '</table></div>' +
        f'<div style="font-size:11px;color:#6b859e;margin-top:8px;">Showing {len(tbl_data):,} of {len(disp_stats):,} SKUs</div>'
    )

    st.markdown(table_html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # SECTION H — Export & Proceed
    # ════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="sc-card-title">Export &amp; Next Steps</div>', unsafe_allow_html=True)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_imp.to_excel(writer,   index=False, sheet_name="Imputation_Output")
        stats_df.to_excel(writer, index=False, sheet_name="SKU_Stats")
    buf.seek(0)

    col_dl1, col_dl2, _ = st.columns([1, 1, 2])
    with col_dl1:
        st.download_button(
            "Download Imputed Data (.xlsx)",
            data=buf.getvalue(),
            file_name="Imputation_Output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch',
        )
    with col_dl2:
        if st.button("Proceed to Forecasting →", type="primary", width='stretch'):
            passing = stats_df[stats_df["pass_filter"]]["SKU"].tolist()
            if not passing:
                st.warning("No SKUs pass current thresholds. Adjust the ADI/CV² sliders above.")
            else:
                s.selected_skus = passing
                s.active_module = "forecast"
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# HELPERS — Upload section (shown only when no data loaded)
# ════════════════════════════════════════════════════════════════════════════

def _render_upload_section():
    """File upload card — shown only when raw_data is None."""
    s = st.session_state

    st.markdown('<div class="sc-card-title" style="margin-bottom:12px">Upload Raw Data File</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded = st.file_uploader(
            "Upload Excel file (.xlsx)",
            type=["xlsx"],
            help="Expected columns: Item No., Year, Month, Monthly_QTY, Opening_Inventory_Qty, Ending_Inventory_Qty",
        )
    with col2:
        st.markdown("""
        <div class="info-box">
            <strong>Required columns:</strong><br>
            • Item No. (or SKU)<br>
            • Year, Month<br>
            • Monthly_QTY<br>
            • Opening_Inventory_Qty<br>
            • Ending_Inventory_Qty<br>
            • Unit_Inventory_Cost<br>
            • m2_Per_Item
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    if not uploaded:
        return

    # Only read the file when it is NEW — skip on every other rerun.
    # st.file_uploader returns the same object on every Streamlit rerun
    # (typing in search, clicking Reset, etc.), so guard with the filename.
    already_staged = (
        s.get("_staged_df") is not None
        and s.get("_staged_filename") == uploaded.name
    )
    if not already_staged:
        with st.spinner("Reading Excel file…"):
            try:
                df = _load_file(uploaded)
            except Exception as e:
                st.markdown(f'<div class="error-box">❌ Failed to read file: {e}</div>', unsafe_allow_html=True)
                return

        ok, msg = _validate_columns(df)
        if not ok:
            st.markdown(f'<div class="error-box">❌ {msg}</div>', unsafe_allow_html=True)
            return

        # Stage the uploaded data — do NOT set s.raw_data yet.
        # raw_data is only committed when user clicks Confirm, ensuring
        # selected_skus is always set before the pipeline runs.
        s._staged_df       = df
        s._staged_filename = uploaded.name
    else:
        # File already read — reuse cached dataframe instantly, no disk I/O
        df = s._staged_df

    skus   = sorted(df["SKU"].unique().tolist())
    n_skus = len(skus)

    # SKU selection
    st.markdown('<div class="sc-card-title">SKU Selection</div>', unsafe_allow_html=True)
    selected_skus = _render_sku_selector(df, skus, n_skus, key_suffix="initial")

    st.markdown(f"""
    <div class="info-box" style="margin-top:12px">
        <strong>{len(selected_skus)} SKUs</strong> will be processed through the full pipeline
        (Imputation → Forecasting → Optimization)
    </div>
    """, unsafe_allow_html=True)

    col_btn1, col_btn2, _ = st.columns([1, 1, 3])
    with col_btn1:
        if st.button("Confirm & Run Imputation", type="primary", width='stretch', key="confirm_btn"):
            # Commit staged data and selected SKUs together atomically
            s.raw_data             = s._staged_df
            s.raw_filename         = s._staged_filename
            s.selected_skus        = selected_skus
            s.n_skus               = len(selected_skus)
            s.imputed_data         = None   # force re-run with correct SKUs
            s.forecast_result      = None
            s.forecast_input_ready = False
            s.optimization_result  = None
            st.rerun()
    with col_btn2:
        if st.button("Reset All", type="secondary", width='stretch', key="reset_btn"):
            for k in ["raw_data", "raw_filename", "selected_skus", "imputed_data",
                      "_staged_df", "_staged_filename",
                      "forecast_result", "forecast_summary", "forecast_fold_df",
                      "forecast_input_ready", "forecast_input_dict", "forecast_input_bytes",
                      "optimization_result"]:
                st.session_state[k] = None
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def _render_sku_selection_inline(df, current_skus, key_suffix="inline"):
    """Compact SKU re-selection inside the expander (data already loaded)."""
    s     = st.session_state
    skus  = sorted(df["SKU"].unique().tolist())
    n_skus = len(skus)

    selected_skus = _render_sku_selector(df, skus, n_skus, key_suffix=key_suffix)

    if st.button("Apply SKU Selection", type="primary", width='content', key=f"apply_sku_{key_suffix}"):
        s.selected_skus        = selected_skus
        s.n_skus               = len(selected_skus)
        s.imputed_data         = None  # force re-imputation
        s.forecast_result      = None
        s.forecast_input_ready = False
        s.optimization_result  = None
        st.rerun()


def _render_sku_selector(df, skus, n_skus, key_suffix=""):
    """Returns list of selected SKUs. Shared by initial and inline selectors."""
    col_a, col_b = st.columns([1, 2])
    with col_a:
        n_select = st.number_input(
            "Number of SKUs to process",
            min_value=1, max_value=n_skus,
            value=min(10, n_skus), step=1,
            help=f"Maximum available: {n_skus} SKUs",
            key=f"n_select_{key_suffix}",
        )
        selection_method = st.selectbox(
            "Selection method",
            ["Top N by Revenue", "Top N by Total Demand", "Manual Selection"],
            key=f"sel_method_{key_suffix}",
        )
    with col_b:
        if selection_method == "Manual selection":
            selected_skus = st.multiselect(
                "Select specific SKUs",
                options=skus,
                default=skus[:min(5, len(skus))],
                max_selections=100,
                key=f"manual_skus_{key_suffix}",
            )
        else:
            grp_col = "SKU"
            sku_counts = (
                df.groupby(grp_col)["Monthly_QTY"].sum()
                if selection_method == "Top N by total demand"
                else df.groupby(grp_col)["Monthly_QTY"].count()
            )
            top_skus      = sku_counts.nlargest(int(n_select)).index.tolist()
            selected_skus = top_skus
            col_label     = "Total Demand" if "demand" in selection_method else "Data Points"

            # ── Styled SKU preview table — matches SKU Classification Table ────
            # Use on_click callback for Reset so it ONLY clears the search key
            # without triggering a full script rerun (which would re-read the file).
            flt_key = f"sku_preview_search_{key_suffix}"

            def _clear_search(k=flt_key):
                st.session_state[k] = ""

            _sc1, _sc2 = st.columns([4, 1])
            with _sc1:
                search_val = st.text_input(
                    "Search", placeholder="Search SKU…",
                    key=flt_key, label_visibility="collapsed",
                )
            with _sc2:
                st.button(
                    "Reset",
                    key=f"sku_preview_reset_btn_{key_suffix}",
                    width="stretch",
                    on_click=_clear_search,
                )

            display_skus = [sk for sk in top_skus if search_val.lower() in sk.lower()] if search_val else top_skus

            # Table styles matching SKU Classification Table exactly
            _th = ("padding:10px 14px;text-align:left;font-size:16px;text-transform:uppercase;"
                   "letter-spacing:.09em;color:#6b859e;font-weight:500;border-bottom:1px solid #243b55;"
                   "white-space:nowrap;")
            _td_sku = ("padding:11px 14px;font-size:16px;color:#f4f8fb;border-bottom:1px solid #1a2e45;"
                       "font-family:DM Mono,monospace;font-weight:500;")
            _td_num = ("padding:11px 14px;font-size:16px;color:#a8c0d4;border-bottom:1px solid #1a2e45;"
                       "white-space:nowrap;text-align:right;")

            rows_html = "".join(
                f'<tr style="border-left:3px solid transparent;">'
                f'<td style="{_td_sku}">{sk}</td>'
                f'<td style="{_td_num}">{round(sku_counts.get(sk, 0), 1)}</td>'
                f'</tr>'
                for sk in display_skus
            )

            table_html = (
                f'<div style="margin-bottom:6px;font-size:11px;color:#6b859e;">'
                f'Showing <strong style="color:#1bb8a0">{len(display_skus)}</strong> of '
                f'<strong style="color:#f4f8fb">{len(top_skus)}</strong> selected SKUs</div>'
                '<div style="overflow-x:auto;overflow-y:auto;max-height:300px;'
                'border-radius:8px;border:1px solid #243b55;margin-top:4px;">'
                '<table style="width:100%;border-collapse:collapse;background:#1d3048;">'
                '<thead><tr style="background:#162535;position:sticky;top:0;z-index:5;">'
                f'<th style="{_th}">SKU</th>'
                f'<th style="{_th};text-align:right">{col_label}</th>'
                '</tr></thead>'
                f'<tbody>{rows_html}</tbody>'
                '</table></div>'
            )
            st.markdown(table_html, unsafe_allow_html=True)
    return selected_skus


# ── File helpers (unchanged from upload.py) ────────────────────────────────────
def _load_file(uploaded_file) -> pd.DataFrame:
    xls   = pd.ExcelFile(uploaded_file)
    sheet = xls.sheet_names[0]
    df    = pd.read_excel(xls, sheet_name=sheet)
    if "Item No." in df.columns and "SKU" not in df.columns:
        df = df.rename(columns={"Item No.": "SKU"})
    for col in ["Year", "Month", "Monthly_QTY", "Opening_Inventory_Qty", "Ending_Inventory_Qty"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["SKU", "Year", "Month"]).copy()
    df["Year"]  = df["Year"].astype(int)
    df["Month"] = df["Month"].astype(int)
    return df


def _validate_columns(df: pd.DataFrame):
    if "SKU" not in df.columns and "Item No." not in df.columns:
        return False, "Missing item identifier column ('SKU' or 'Item No.')."
    for col in ["Year", "Month", "Monthly_QTY", "Opening_Inventory_Qty", "Ending_Inventory_Qty"]:
        if col not in df.columns:
            return False, f"Missing required column: '{col}'"
    return True, "OK"
