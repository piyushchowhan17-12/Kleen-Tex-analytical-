"""
Plotly chart helpers — all charts use the navy/teal/amber design tokens.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots

# ── Design tokens ──────────────────────────────────────────────────────────────
NAVY    = "#0d1b2a"
NAVY2   = "#1a2e45"
NAVY3   = "#243b55"
CARD    = "#162535"
CARD2   = "#1d3048"
BORDER  = "#243b55"
TEAL    = "#1bb8a0"
TEAL2   = "#0d9b87"
AMBER   = "#f5a623"
ROSE    = "#e05c7a"
SLATE   = "#8fa3b8"
WHITE   = "#f4f8fb"
TEXT2   = "#a8c0d4"
TEXT3   = "#6b859e"

FONT_FAMILY = "DM Sans, sans-serif"
MONO_FONT   = "DM Mono, monospace"

BASE_LAYOUT = dict(
    paper_bgcolor=CARD,
    plot_bgcolor=CARD2,
    font=dict(family=FONT_FAMILY, color=TEXT2, size=12),
    margin=dict(l=50, r=20, t=40, b=40),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        bordercolor=BORDER,
        borderwidth=1,
        font=dict(size=11, color=TEXT2),
    ),
    xaxis=dict(
        gridcolor=BORDER,
        linecolor=BORDER,
        tickcolor=BORDER,
        tickfont=dict(color=TEXT3, size=11),
        title_font=dict(color=TEXT3, size=11),
        zeroline=False,
    ),
    yaxis=dict(
        gridcolor=BORDER,
        linecolor=BORDER,
        tickcolor=BORDER,
        tickfont=dict(color=TEXT3, size=11),
        title_font=dict(color=TEXT3, size=11),
        zeroline=False,
    ),
    hoverlabel=dict(
        bgcolor=NAVY3,
        bordercolor=BORDER,
        font=dict(family=FONT_FAMILY, color=WHITE, size=12),
    ),
)


def _apply_base(fig, title="", height=320):
    layout = dict(**BASE_LAYOUT, height=height)
    if title:
        layout["title"] = dict(text=title, font=dict(family="Fraunces, serif", size=16, color=WHITE), x=0.01)
    fig.update_layout(**layout)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 1. TIME-SERIES: raw vs imputed vs forecast
# ─────────────────────────────────────────────────────────────────────────────
def ts_chart(sku_df: pd.DataFrame, sku_id: str, show_forecast=True, height=360) -> go.Figure:
    """
    Draw raw / imputed / forecast for a single SKU.
    sku_df must have columns: Date, Monthly_QTY, Imputed_Demand, Demand_Prediction (optional)
    """
    df = sku_df.copy().sort_values("Date")

    fig = go.Figure()

    # Raw (historical)
    hist = df[df["Year"] < 2025] if "Year" in df.columns else df[df["Demand_Prediction"].isna()]
    fig.add_trace(go.Scatter(
        x=hist["Date"], y=hist["Monthly_QTY"],
        mode="lines",
        name="Raw Demand",
        line=dict(color=SLATE, width=1.5, dash="dot"),
        opacity=0.7,
    ))

    # Imputed
    fig.add_trace(go.Scatter(
        x=hist["Date"], y=hist["Imputed_Demand"],
        mode="lines+markers",
        name="Imputed Demand",
        line=dict(color=TEAL, width=2),
        marker=dict(size=4, color=TEAL),
    ))

    # Forecast
    if show_forecast and "Demand_Prediction" in df.columns:
        fc = df[df["Demand_Prediction"].notna()]
        if not fc.empty:
            # Connect imputed to forecast
            last_hist = hist.iloc[-1:] if not hist.empty else pd.DataFrame()
            if not last_hist.empty:
                bridge = pd.DataFrame({
                    "Date": [last_hist["Date"].values[-1], fc["Date"].values[0]],
                    "val": [last_hist["Imputed_Demand"].values[-1], fc["Demand_Prediction"].values[0]],
                })
                fig.add_trace(go.Scatter(
                    x=bridge["Date"], y=bridge["val"],
                    mode="lines",
                    line=dict(color=AMBER, width=1.5, dash="dash"),
                    showlegend=False,
                    hoverinfo="skip",
                ))

            fig.add_trace(go.Scatter(
                x=fc["Date"], y=fc["Demand_Prediction"],
                mode="lines+markers",
                name="Forecast",
                line=dict(color=AMBER, width=2.5),
                marker=dict(size=6, color=AMBER, symbol="diamond"),
            ))

            # Forecast shaded region
            fig.add_vrect(
                x0=fc["Date"].min(), x1=fc["Date"].max(),
                fillcolor=AMBER, opacity=0.04,
                layer="below", line_width=0,
            )

    fig = _apply_base(fig, title=f"Demand Series — {sku_id}", height=height)
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Quantity",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 2. ADI vs CV² SCATTER
# ─────────────────────────────────────────────────────────────────────────────
def adi_cv2_scatter(stats_df: pd.DataFrame, adi_thresh: float, cv2_thresh: float,
                    selected_sku: str = None, height=300) -> go.Figure:
    """
    Scatter plot of ADI vs CV² for all SKUs, colored by pass/fail.
    stats_df must have: SKU, ADI, CV2, pass_filter
    """
    df = stats_df.copy()
    pass_df = df[df["pass_filter"] == True]
    fail_df = df[df["pass_filter"] == False]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=fail_df["ADI"], y=fail_df["CV2"],
        mode="markers",
        name="Excluded",
        marker=dict(color=ROSE, size=5, opacity=0.5),
        text=fail_df["SKU"],
        hovertemplate="<b>%{text}</b><br>ADI: %{x:.2f}<br>CV²: %{y:.2f}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=pass_df["ADI"], y=pass_df["CV2"],
        mode="markers",
        name="Pass",
        marker=dict(color=TEAL, size=5, opacity=0.75),
        text=pass_df["SKU"],
        hovertemplate="<b>%{text}</b><br>ADI: %{x:.2f}<br>CV²: %{y:.2f}<extra></extra>",
    ))

    # Threshold lines
    fig.add_hline(y=cv2_thresh, line_dash="dash", line_color=AMBER, line_width=1.2,
                  annotation_text=f"CV²={cv2_thresh}", annotation_font_color=AMBER,
                  annotation_font_size=10)
    fig.add_vline(x=adi_thresh, line_dash="dash", line_color=AMBER, line_width=1.2,
                  annotation_text=f"ADI={adi_thresh}", annotation_font_color=AMBER,
                  annotation_font_size=10)

    if selected_sku and selected_sku in df["SKU"].values:
        sel = df[df["SKU"] == selected_sku].iloc[0]
        fig.add_trace(go.Scatter(
            x=[sel["ADI"]], y=[sel["CV2"]],
            mode="markers",
            name="Selected",
            marker=dict(color=AMBER, size=12, symbol="star"),
        ))

    fig = _apply_base(fig, title="ADI vs CV² Classification", height=height)
    fig.update_layout(xaxis_title="ADI", yaxis_title="CV²")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 3. DEMAND TYPE DONUT
# ─────────────────────────────────────────────────────────────────────────────
def demand_type_donut(type_counts: dict, height=240) -> go.Figure:
    colors = {
        "smooth":       TEAL,
        "erratic":      AMBER,
        "intermittent": ROSE,
        "insufficient": SLATE,
    }
    labels = list(type_counts.keys())
    values = list(type_counts.values())
    clrs   = [colors.get(l, SLATE) for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.6,
        marker=dict(colors=clrs, line=dict(color=CARD, width=2)),
        textfont=dict(size=11, color=WHITE),
        hovertemplate="<b>%{label}</b><br>%{value} SKUs (%{percent})<extra></extra>",
    ))

    total = sum(values)
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:10px'>SKUs</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=18, color=WHITE, family=MONO_FONT),
        align="center",
    )

    fig = _apply_base(fig, title="Demand Type Distribution", height=height)
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=40, b=30),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 4. IMPUTATION COMPARISON (dual line)
# ─────────────────────────────────────────────────────────────────────────────
def imputation_comparison_chart(sku_df: pd.DataFrame, sku_id: str, height=260) -> go.Figure:
    df = sku_df.copy().sort_values("Date")
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Monthly_QTY"],
        mode="lines",
        name="Raw (Monthly_QTY)",
        line=dict(color=SLATE, width=1.5),
        opacity=0.8,
    ))
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Imputed_Demand"],
        mode="lines+markers",
        name="Imputed Demand",
        line=dict(color=TEAL, width=2),
        marker=dict(size=4),
        fill="tonexty",
        fillcolor="rgba(27,184,160,0.07)",
    ))

    # Highlight imputed points
    changed = df[df["Monthly_QTY"] != df["Imputed_Demand"]]
    if not changed.empty:
        fig.add_trace(go.Scatter(
            x=changed["Date"], y=changed["Imputed_Demand"],
            mode="markers",
            name="Imputed Points",
            marker=dict(color=AMBER, size=8, symbol="circle-open", line=dict(width=2, color=AMBER)),
        ))

    fig = _apply_base(fig, title=f"Raw vs Imputed — {sku_id}", height=height)
    fig.update_layout(xaxis_title="", yaxis_title="Quantity")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 5. MODEL PERFORMANCE BAR
# ─────────────────────────────────────────────────────────────────────────────
def model_perf_bar(summary_df: pd.DataFrame, height=280) -> go.Figure:
    """Bar chart of average MAPE per model.
    Accepts either 'Avg_Val_MAPE' (forecasting.py output) or
    'Average_Validation_MAPE' (legacy) as the MAPE column name.
    """
    # Resolve whichever column name is present
    if "Avg_Val_MAPE" in summary_df.columns:
        mape_col = "Avg_Val_MAPE"
    elif "Average_Validation_MAPE" in summary_df.columns:
        mape_col = "Average_Validation_MAPE"
    else:
        # Nothing to plot — return empty figure with a message
        fig = go.Figure()
        fig.add_annotation(text="No MAPE data available", x=0.5, y=0.5,
                           xref="paper", yref="paper", showarrow=False,
                           font=dict(color=SLATE, size=13))
        return _apply_base(fig, title="Average Validation MAPE by Model", height=height)

    # Resolve model column name
    model_col = "Best_Model_Used" if "Best_Model_Used" in summary_df.columns else summary_df.columns[0]

    df = summary_df[[model_col, mape_col]].copy()
    df[mape_col] = pd.to_numeric(df[mape_col], errors="coerce")
    grp = df.groupby(model_col)[mape_col].mean().reset_index()
    grp = grp.sort_values(mape_col).reset_index(drop=True)

    clrs = [TEAL if i == 0 else CARD2 for i in range(len(grp))]

    fig = go.Figure(go.Bar(
        x=grp[model_col],
        y=grp[mape_col],
        marker=dict(color=clrs, line=dict(color=BORDER, width=1)),
        text=[f"{v:.1f}%" if pd.notna(v) else "N/A" for v in grp[mape_col]],
        textposition="outside",
        textfont=dict(color=TEXT2, size=11),
        hovertemplate="<b>%{x}</b><br>Avg MAPE: %{y:.2f}%<extra></extra>",
    ))

    fig = _apply_base(fig, title="Average Validation MAPE by Model", height=height)
    fig.update_layout(xaxis_title="", yaxis_title="MAPE (%)")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 6. FORECAST HORIZON BAR (multi-SKU comparison)
# ─────────────────────────────────────────────────────────────────────────────
def forecast_comparison_bar(fc_df: pd.DataFrame, skus: list, height=320) -> go.Figure:
    """
    Grouped bar: predicted demand per month for selected SKUs.
    fc_df: Demand_Prediction rows with SKU, Month, Year, Demand_Prediction
    """
    df = fc_df[fc_df["SKU"].isin(skus) & fc_df["Demand_Prediction"].notna()].copy()
    if df.empty:
        return go.Figure()

    df["Period"] = df["Year"].astype(str) + "-M" + df["Month"].astype(str).str.zfill(2)
    colors = [TEAL, AMBER, ROSE, SLATE, "#7c6af0", "#4ac8f0"]

    fig = go.Figure()
    for idx, sku in enumerate(skus):
        s = df[df["SKU"] == sku]
        fig.add_trace(go.Bar(
            x=s["Period"], y=s["Demand_Prediction"],
            name=sku,
            marker_color=colors[idx % len(colors)],
        ))

    fig = _apply_base(fig, title="Forecast by SKU", height=height)
    fig.update_layout(barmode="group", xaxis_title="Period", yaxis_title="Predicted Demand")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 7. OPTIMIZATION: inventory trajectory
# ─────────────────────────────────────────────────────────────────────────────
def inventory_trajectory(plan_df: pd.DataFrame, item: str, height=320) -> go.Figure:
    df = plan_df[plan_df["Item"] == item].copy()
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["Period"].astype(str), y=df["I_it_Open"],
        mode="lines+markers", name="Opening Inv.",
        line=dict(color=TEAL, width=2),
        marker=dict(size=5),
    ))
    fig.add_trace(go.Scatter(
        x=df["Period"].astype(str), y=df["I_it_End"],
        mode="lines+markers", name="Ending Inv.",
        line=dict(color=TEAL2, width=1.5, dash="dash"),
        marker=dict(size=4),
    ))
    fig.add_trace(go.Bar(
        x=df["Period"].astype(str), y=df["Q_it"],
        name="Order Qty",
        marker_color=AMBER,
        opacity=0.7,
        yaxis="y2",
    ))
    fig.add_trace(go.Bar(
        x=df["Period"].astype(str), y=df["D_it"],
        name="Demand",
        marker_color=ROSE,
        opacity=0.5,
        yaxis="y2",
    ))

    fig = _apply_base(fig, title=f"Inventory Trajectory — {item}", height=height)
    fig.update_layout(
        yaxis=dict(title="Inventory Level", side="left"),
        yaxis2=dict(title="Qty", overlaying="y", side="right", showgrid=False),
        barmode="group",
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 8. CAPACITY UTILIZATION
# ─────────────────────────────────────────────────────────────────────────────
def capacity_utilization_chart(cap_df: pd.DataFrame, height=260) -> go.Figure:
    df = cap_df.copy()
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["Period"].astype(str),
        y=df["Capacity_Utilization_%"],
        marker=dict(
            color=[ROSE if v > 90 else (AMBER if v > 70 else TEAL) for v in df["Capacity_Utilization_%"]],
            line=dict(color=BORDER, width=0.5),
        ),
        text=[f"{v:.1f}%" for v in df["Capacity_Utilization_%"]],
        textposition="outside",
        hovertemplate="Period: %{x}<br>Utilization: %{y:.2f}%<extra></extra>",
    ))

    fig.add_hline(y=80, line_dash="dash", line_color=AMBER, line_width=1,
                  annotation_text="80% warning", annotation_font_color=AMBER, annotation_font_size=10)

    fig = _apply_base(fig, title="Warehouse Capacity Utilization %", height=height)
    fig.update_layout(yaxis_title="Utilization (%)", yaxis_range=[0, 110])
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 9. OBJECTIVE BREAKDOWN WATERFALL
# ─────────────────────────────────────────────────────────────────────────────
def objective_waterfall(obj_df: pd.DataFrame, height=280) -> go.Figure:
    df = obj_df[obj_df["Objective Component"] != "Total"].copy()
    total_row = obj_df[obj_df["Objective Component"] == "Total"]

    labels = df["Objective Component"].tolist()
    vals   = df["Value"].tolist()
    clrs   = [TEAL, AMBER, ROSE]

    fig = go.Figure(go.Bar(
        x=labels, y=vals,
        marker=dict(color=clrs[:len(labels)], line=dict(color=BORDER, width=1)),
        text=[f"${v:,.0f}" for v in vals],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Cost: $%{y:,.2f}<extra></extra>",
    ))

    if not total_row.empty:
        total_val = float(total_row["Value"].values[0])
        fig.add_annotation(
            x=0.98, y=0.98, xref="paper", yref="paper",
            text=f"<b>Total: ${total_val:,.0f}</b>",
            showarrow=False,
            bgcolor=NAVY3, bordercolor=TEAL, borderwidth=1,
            font=dict(size=13, color=TEAL, family=MONO_FONT),
            align="right",
        )

    fig = _apply_base(fig, title="Objective Function Breakdown", height=height)
    fig.update_layout(yaxis_title="Cost ($)")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 10. SKU ORDER ACTIVITY HEATMAP
# ─────────────────────────────────────────────────────────────────────────────
def order_heatmap(plan_df: pd.DataFrame, max_items=30, height=400) -> go.Figure:
    """Binary order/no-order heatmap across periods per item."""
    pivot = plan_df.pivot_table(index="Item", columns="Period", values="B_it", aggfunc="first")
    pivot = pivot.head(max_items)

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[str(c) for c in pivot.columns],
        y=pivot.index.tolist(),
        colorscale=[[0, CARD2], [1, TEAL]],
        showscale=False,
        hovertemplate="Item: %{y}<br>Period: %{x}<br>Order: %{z}<extra></extra>",
        xgap=1, ygap=1,
    ))

    fig = _apply_base(fig, title="Order Activity Heatmap (1 = order placed)", height=height)
    fig.update_layout(
        xaxis=dict(side="bottom", tickangle=-45, tickfont=dict(size=10)),
        yaxis=dict(tickfont=dict(size=10), autorange="reversed"),
        margin=dict(l=130, r=20, t=50, b=60),
    )
    return fig
