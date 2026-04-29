"""
Module 3 — Inventory Optimization.
Uses exact functions from kleen_tex_scip_model_v3_jun_nov.py:
  read_input_data_from_dict() → build_parameters() → solve_model() → extract_results()
"""

import io
import warnings
warnings.filterwarnings("ignore")

from typing import Dict, List, Tuple

import streamlit as st
import pandas as pd
import numpy as np


# ══════════════════════════════════════════════════════════════════════════════
# EXACT PORT OF kleen_tex_scip_model_v3_jun_nov.py
# No logic changed — only adapted to accept in-memory data_dict instead of file.
# ══════════════════════════════════════════════════════════════════════════════

# Constants — exact copy from source file
DEFAULT_F_I              = 500.0
DEFAULT_C                = 500_000.0
HIDE_SOLVER_LOG          = True
INITIAL_INVENTORY_PERIOD = 1


def read_input_data_from_dict(data_dict: dict):
    """
    Equivalent of read_input_data(excel_file) from kleen_tex_scip_model_v3_jun_nov.py.
    Accepts in-memory data_dict built by opt_input_builder.
    Returns: I, T, demand_df, I_ini, H, Area  — identical to original.
    """
    demand_pivot      = data_dict["demand_pivot"]       # Predicted_Demand sheet
    iini_pivot        = data_dict["iini_pivot"]          # I_ini wide matrix
    inventory_cost_df = data_dict["inventory_cost"]
    m2_df             = data_dict["m2_per_item"]
    selected_items    = data_dict.get("selected_items", [])
    month_cols        = data_dict.get("month_cols", [])

    # ── Mirror read_period_matrix_sheet() for demand ──────────────────────────
    # T_all from demand pivot columns (numeric months)
    T_all = sorted([c for c in demand_pivot.columns if c != "Item No."])

    demand_df = demand_pivot.set_index("Item No.").copy()
    demand_df.index = demand_df.index.astype(str).str.strip()
    demand_df = demand_df.apply(pd.to_numeric, errors="coerce").fillna(0.0)

    # ── Mirror read_period_matrix_sheet() for I_ini ───────────────────────────
    iini_df = iini_pivot.set_index("Item No.").copy()
    iini_df.index = iini_df.index.astype(str).str.strip()
    iini_df = iini_df.apply(pd.to_numeric, errors="coerce").fillna(0.0)

    # Check periods match — exact logic from original
    T_iini_all = sorted([c for c in iini_df.columns])
    # (we tolerate non-matching if INITIAL_INVENTORY_PERIOD is present)

    # Use ALL periods from the workbook — exact from kleen_tex_scip_model_v3_workbook_aligned.py
    T = T_all
    demand_df = demand_df[[c for c in T if c in demand_df.columns]]

    # Scalar I_ini_i from chosen period column — exact from original
    # I_ini_all = iini_matrix[INITIAL_INVENTORY_PERIOD].to_dict()
    if INITIAL_INVENTORY_PERIOD in iini_df.columns:
        I_ini_all = iini_df[INITIAL_INVENTORY_PERIOD].to_dict()
    else:
        # Fallback: use first available column
        first_col = iini_df.columns[0] if len(iini_df.columns) > 0 else None
        I_ini_all = iini_df[first_col].to_dict() if first_col is not None else {}

    # ── Inventory Cost sheet — exact from original ────────────────────────────
    inventory_cost_df = inventory_cost_df.rename(columns=lambda x: str(x).strip())
    required_cost_cols = {"Item No.", "Unit Inventory Cost"}
    if required_cost_cols.issubset(set(inventory_cost_df.columns)):
        inventory_cost_df["Item No."] = inventory_cost_df["Item No."].astype(str).str.strip()
        inventory_cost_df["Unit Inventory Cost"] = pd.to_numeric(
            inventory_cost_df["Unit Inventory Cost"], errors="coerce").fillna(0.0)
        H_all = dict(zip(inventory_cost_df["Item No."], inventory_cost_df["Unit Inventory Cost"]))
    else:
        # Fallback: use first two columns
        c0 = inventory_cost_df.columns[0]
        c1 = inventory_cost_df.columns[1] if len(inventory_cost_df.columns) > 1 else c0
        inventory_cost_df[c0] = inventory_cost_df[c0].astype(str).str.strip()
        inventory_cost_df[c1] = pd.to_numeric(inventory_cost_df[c1], errors="coerce").fillna(1.0)
        H_all = dict(zip(inventory_cost_df[c0], inventory_cost_df[c1]))

    # ── Area sheet — exact from original ─────────────────────────────────────
    m2_df = m2_df.rename(columns=lambda x: str(x).strip())
    required_area_cols = {"Item No.", "m2/item"}
    if required_area_cols.issubset(set(m2_df.columns)):
        m2_df["Item No."] = m2_df["Item No."].astype(str).str.strip()
        m2_df["m2/item"]  = pd.to_numeric(m2_df["m2/item"], errors="coerce").fillna(0.0)
        Area_all = dict(zip(m2_df["Item No."], m2_df["m2/item"]))
    else:
        c0 = m2_df.columns[0]
        c1 = m2_df.columns[1] if len(m2_df.columns) > 1 else c0
        m2_df[c0] = m2_df[c0].astype(str).str.strip()
        m2_df[c1] = pd.to_numeric(m2_df[c1], errors="coerce").fillna(0.01)
        Area_all = dict(zip(m2_df[c0], m2_df[c1]))

    # ── Filter items — exact logic from original ──────────────────────────────
    # I = list(demand_df.index)
    # I = [i for i in I if i in I_ini_all and i in H_all and i in Area_all]
    I = list(demand_df.index)
    I = [i for i in I if i in I_ini_all and i in H_all and i in Area_all]

    # If selected_items list exists and is not empty, use it — exact from original
    if selected_items:
        selected_set = set(str(x) for x in selected_items)
        I = [i for i in I if i in selected_set]

    demand_df = demand_df.loc[I]
    I_ini = {i: float(I_ini_all[i]) for i in I}
    H     = {i: float(H_all[i])     for i in I}
    Area  = {i: float(Area_all[i])  for i in I}

    return I, T, demand_df, I_ini, H, Area


def build_parameters(I, demand_df, I_ini, H, Area,
                     F_value=DEFAULT_F_I,
                     C=DEFAULT_C):
    """
    Exact copy of build_parameters() from kleen_tex_scip_model_v3_jun_nov.py.
    Note: no ShortageCost — V3 only has Z1 + Z2.
    """
    F = {i: float(F_value) for i in I}
    M = {}
    for i in I:
        raw_M = float(I_ini[i] + demand_df.loc[i].sum() + demand_df.loc[i].max())
        M[i] = max(1.0, raw_M)
    return H, Area, F, float(C), M


def get_prev_inventory_expr(i, t_index, T, I_ini, I_End):
    """
    Exact copy of get_prev_inventory_expr() from kleen_tex_scip_model_v3_jun_nov.py.
    Returns I_ini[i] for first period, I_End[i, T[t_index-1]] for subsequent.
    """
    if t_index == 0:
        return I_ini[i]
    return I_End[i, T[t_index - 1]]


def solve_model(I, T, demand_df, I_ini, H, Area, F, C, M):
    """
    Exact copy of solve_model() from kleen_tex_scip_model_v3_jun_nov.py.
    Variables: Q, s, S, I_End, B.
    Objective: Min Z1 (holding) + Z2 (setup).
    """
    from pyscipopt import Model, quicksum

    model = Model("KleenTex_Professor_Model_V3")
    model.hideOutput(HIDE_SOLVER_LOG)

    Q     = {}
    s     = {}
    S     = {}
    I_End = {}
    B     = {}

    for i in I:
        s[i] = model.addVar(lb=0, vtype="C", name=f"s[{i}]")
        S[i] = model.addVar(lb=0, vtype="C", name=f"S[{i}]")
        for t in T:
            Q[i, t]     = model.addVar(lb=0, vtype="C", name=f"Q[{i},{t}]")
            I_End[i, t] = model.addVar(lb=0, vtype="C", name=f"I_End[{i},{t}]")
            B[i, t]     = model.addVar(vtype="B",        name=f"B[{i},{t}]")

    # Objective: Min Z1 + Z2 — exact from original
    Z1_terms = []
    for i in I:
        for t_idx, t in enumerate(T):
            prev_inv = get_prev_inventory_expr(i, t_idx, T, I_ini, I_End)
            Z1_terms.append(((prev_inv + I_End[i, t]) / 2.0) * H[i])

    Z1 = quicksum(Z1_terms)
    Z2 = quicksum(B[i, t] * F[i] for i in I for t in T)
    model.setObjective(Z1 + Z2, "minimize")

    # Inventory balance — exact from original
    for i in I:
        for t_idx, t in enumerate(T):
            D_it     = float(demand_df.loc[i, t])
            prev_inv = get_prev_inventory_expr(i, t_idx, T, I_ini, I_End)
            model.addCons(
                I_End[i, t] == prev_inv + Q[i, t] - D_it,
                name=f"InventoryBalance[{i},{t}]"
            )

    # Trigger logic — exact from original
    for i in I:
        for t_idx, t in enumerate(T):
            prev_inv = get_prev_inventory_expr(i, t_idx, T, I_ini, I_End)
            model.addCons(
                prev_inv <= s[i] - 1 + M[i] * (1 - B[i, t]),
                name=f"TriggerUpper[{i},{t}]"
            )
            model.addCons(
                prev_inv >= s[i] - M[i] * B[i, t],
                name=f"TriggerLower[{i},{t}]"
            )

    # Order-up-to logic — exact from original
    for i in I:
        for t_idx, t in enumerate(T):
            prev_inv = get_prev_inventory_expr(i, t_idx, T, I_ini, I_End)
            model.addCons(
                prev_inv + Q[i, t] >= -M[i] * (1 - B[i, t]) + S[i],
                name=f"OrderUpToLower[{i},{t}]"
            )
            model.addCons(
                prev_inv + Q[i, t] <= M[i] * (1 - B[i, t]) + S[i],
                name=f"OrderUpToUpper[{i},{t}]"
            )

    # Production activation — exact from original
    for i in I:
        for t in T:
            model.addCons(
                Q[i, t] <= M[i] * B[i, t],
                name=f"ProductionActivation[{i},{t}]"
            )

    # s_i + 1 <= S_i — exact from original
    for i in I:
        model.addCons(s[i] + 1 <= S[i], name=f"sLessThanS[{i}]")

    # Capacity — exact from original
    for t_idx, t in enumerate(T):
        model.addCons(
            quicksum(
                (get_prev_inventory_expr(i, t_idx, T, I_ini, I_End) + Q[i, t]) * Area[i]
                for i in I
            ) <= C,
            name=f"WarehouseCapacity[{t}]"
        )

    model.optimize()
    return model, Q, s, S, I_End, B


def extract_results(model, I, T, demand_df, I_ini, Q, s, S, I_End, B, H, Area, F, C):
    """
    Exact copy of extract_results() from kleen_tex_scip_model_v3_jun_nov.py.
    Returns policy_df, plan_df, objective_df, capacity_df.
    Note: plan_df uses Prev_Inventory column (exact from source file).
    """
    # Policy levels
    policy_rows = []
    for i in I:
        policy_rows.append({
            "Item":                  i,
            "s_i":                   round(model.getVal(s[i]), 2),
            "S_i":                   round(model.getVal(S[i]), 2),
            "H_i_UnitInventoryCost": round(H[i], 4),
            "Area_m2_per_item":      round(Area[i], 4),
        })
    policy_df = pd.DataFrame(policy_rows)

    # Period results — exact from original
    plan_rows = []
    for i in I:
        for t_idx, t in enumerate(T):
            prev_inv = I_ini[i] if t_idx == 0 else model.getVal(I_End[i, T[t_idx - 1]])
            q_val    = model.getVal(Q[i, t])
            plan_rows.append({
                "Item":              i,
                "Period":            t,
                "Prev_Inventory":     round(prev_inv, 2),
                "B_it":              int(round(model.getVal(B[i, t]))),
                "Q_it":              round(q_val, 2),
                "D_it":              round(float(demand_df.loc[i, t]), 2),
                "I_it_End":          round(model.getVal(I_End[i, t]), 2),
                "Area_m2_per_item":  round(Area[i], 4),
                "Used_Area_m2":      round(Area[i] * (prev_inv + q_val), 4),
            })
    plan_df = pd.DataFrame(plan_rows)

    # Objective breakdown — exact from original (Z1 + Z2 only, no Z3)
    z1_value = 0.0
    for i in I:
        for t_idx, t in enumerate(T):
            prev_inv = I_ini[i] if t_idx == 0 else model.getVal(I_End[i, T[t_idx - 1]])
            z1_value += ((prev_inv + model.getVal(I_End[i, t])) / 2.0) * H[i]

    z2_value = sum(model.getVal(B[i, t]) * F[i] for i in I for t in T)

    objective_df = pd.DataFrame({
        "Objective Component": [
            "Z1: Warehouse Holding Cost",
            "Z2: Fixed Production Cost",
            "Total",
        ],
        "Value": [
            round(z1_value, 2),
            round(z2_value, 2),
            round(model.getObjVal(), 2),
        ],
    })

    # Capacity usage — exact from original
    capacity_rows = []
    for t_idx, t in enumerate(T):
        used_area = 0.0
        for i in I:
            prev_inv = I_ini[i] if t_idx == 0 else model.getVal(I_End[i, T[t_idx - 1]])
            used_area += (prev_inv + model.getVal(Q[i, t])) * Area[i]
        capacity_rows.append({
            "Period":                 t,
            "Used_Area_m2":           round(used_area, 4),
            "Warehouse_Capacity_m2":  C,
            "Capacity_Utilization_%": round((used_area / C) * 100, 2) if C != 0 else 0,
        })
    capacity_df = pd.DataFrame(capacity_rows)

    return policy_df, plan_df, objective_df, capacity_df


def _run_heuristic_fallback(I, T, demand_df, I_ini, H, Area, F_val, C):
    """
    V3-compatible heuristic: s = avg - std, S = avg + std.
    No shortage variable (matching V3 model which has no Z3).
    Used only when pyscipopt is not installed.
    """
    policy_rows = []
    plan_rows   = []
    Z1 = Z2 = 0.0

    for i in I:
        d   = demand_df.loc[i].astype(float).values
        pos = d[d > 0]
        avg = float(np.mean(pos)) if len(pos) > 0 else 1.0
        std = float(np.std(d))    if len(d) > 1  else 0.0
        s_v = max(0.0, avg - std)
        S_v = max(s_v + 1.0, avg * 2.0)
        inv = float(I_ini.get(i, 0.0))
        h   = float(H.get(i, 1.0))
        a   = float(Area.get(i, 0.01))

        policy_rows.append({
            "Item": i, "s_i": round(s_v, 2), "S_i": round(S_v, 2),
            "H_i_UnitInventoryCost": round(h, 4), "Area_m2_per_item": round(a, 4),
        })

        for t_idx, t in enumerate(T):
            D     = float(demand_df.loc[i, t])
            b     = 1 if inv <= s_v else 0
            q     = max(0.0, S_v - inv) if b else 0.0
            end   = max(0.0, inv + q - D)
            Z1   += ((inv + end) / 2.0) * h
            Z2   += b * F_val
            plan_rows.append({
                "Item": i, "Period": t,
                "Prev_Inventory": round(inv, 2), "B_it": b, "Q_it": round(q, 2),
                "D_it": round(D, 2), "I_it_End": round(end, 2),
                "Area_m2_per_item": round(a, 4), "Used_Area_m2": round(a * (inv + q), 4),
            })
            inv = end

    total = round(Z1 + Z2, 2)
    obj_df = pd.DataFrame({
        "Objective Component": [
            "Z1: Warehouse Holding Cost", "Z2: Fixed Production Cost", "Total"],
        "Value": [round(Z1, 2), round(Z2, 2), total],
    })
    plan_df = pd.DataFrame(plan_rows)
    cap_rows = []
    for t in T:
        used = float(plan_df[plan_df["Period"] == t]["Used_Area_m2"].sum())
        cap_rows.append({
            "Period": t, "Used_Area_m2": round(used, 4),
            "Warehouse_Capacity_m2": C,
            "Capacity_Utilization_%": round((used / C) * 100, 2) if C else 0,
        })
    return (pd.DataFrame(policy_rows), plan_df, obj_df, pd.DataFrame(cap_rows), total)

# ══════════════════════════════════════════════════════════════════════════════
# Streamlit UI
# ══════════════════════════════════════════════════════════════════════════════
def render():
    s = st.session_state

    has_fc_input = s.get("forecast_input_ready") is True
    has_result   = isinstance(s.get("optimization_result"), dict)

    st.markdown(f"""
    <div class="topbar">
        <div>
            <div class="topbar-title">⚙️ Module 3 — Inventory Optimization</div>
            <div class="topbar-sub">(s,S) policy · SCIP solver · Minimize Z₁ holding + Z₂ setup</div>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
            {'<span class="badge-pill pill-teal">✓ Solution Found</span>' if has_result else '<span class="badge-pill pill-slate">⏳ Not Run</span>'}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not has_fc_input:
        st.markdown('<div class="warn-box">⚠️ Please run the Forecasting module first.</div>',
                    unsafe_allow_html=True)

    # ── Input source — auto pipeline only ────────────────────────────────────
    data_dict = None

    if has_fc_input and s.get("forecast_input_dict"):
        data_dict = s.forecast_input_dict
    else:
        st.markdown('<div class="warn-box">⚠️ No pipeline output. Please run the Forecasting module first.</div>',
                    unsafe_allow_html=True)

    # ── Solver parameters ────────────────────────────────────────────────────
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        warehouse_cap = st.number_input("Warehouse Capacity (m²)",
            min_value=1_000.0, max_value=10_000_000.0,
            value=float(s.get("warehouse_capacity", DEFAULT_C)),
            step=1_000.0, format="%.0f")
        s.warehouse_capacity = warehouse_cap
    with col_p2:
        fixed_order = st.number_input("Fixed Order Cost F_i ($/order)",
            min_value=0.0, max_value=100_000.0,
            value=float(s.get("fixed_order_cost", DEFAULT_F_I)),
            step=10.0, format="%.2f")
        s.fixed_order_cost = fixed_order

    col_run, col_clr, _ = st.columns([1, 1, 4])
    with col_run:
        run_btn = st.button("🚀 Solve Optimization", type="primary",
                            use_container_width=True, disabled=(data_dict is None))
    with col_clr:
        if st.button("🔄 Clear Results", type="secondary", use_container_width=True):
            s.optimization_result = None
            st.rerun()

    # ── Run ──────────────────────────────────────────────────────────────────
    if run_btn and data_dict is not None:
        _run_optimization(data_dict, warehouse_cap, fixed_order, s)

    if has_result:
        _render_results(s)


def _run_optimization(data_dict, warehouse_cap, fixed_order, s):
    # Check SCIP available
    try:
        import pyscipopt  # noqa
        scip_ok = True
    except ImportError:
        scip_ok = False

    if not scip_ok:
        st.markdown("""
        <div class="warn-box">
            ⚠️ <strong>PySCIPOpt not installed.</strong>
            Install with: <code>pip install pyscipopt</code><br>
            Running heuristic (s,S) fallback instead.
        </div>""", unsafe_allow_html=True)
        _run_heuristic_ui(data_dict, warehouse_cap, fixed_order, s)
        return

    with st.spinner("🔧 Building and solving SCIP model…"):
        try:
            # Use your exact original function chain
            I, T, demand_df, I_ini, H, Area = read_input_data_from_dict(data_dict)
            H, Area, F, C, M = build_parameters(
                I, demand_df, I_ini, H, Area,
                F_value=fixed_order, C=warehouse_cap,
            )
            model, Q, sv, Sv, I_End, B = solve_model(
                I, T, demand_df, I_ini, H, Area, F, C, M)

            status = str(model.getStatus()).lower()
            if status not in ["optimal", "bestsolfound"]:
                raise ValueError(f"Solver status: {model.getStatus()}")

            policy_df, plan_df, obj_df, cap_df = extract_results(
                model, I, T, demand_df, I_ini, Q, sv, Sv, I_End, B,
                H, Area, F, C,
            )
            s.optimization_result = {
                "objective": round(model.getObjVal(), 2),
                "status":    "optimal",
                "policy_df": policy_df,
                "plan_df":   plan_df,
                "obj_df":    obj_df,
                "cap_df":    cap_df,
            }
            st.success(f"✅ Optimal solution found! Objective: ${model.getObjVal():,.2f}")
            st.rerun()

        except Exception as e:
            st.markdown(f'<div class="error-box">❌ SCIP error: {e}</div>', unsafe_allow_html=True)
            import traceback
            with st.expander("Error details"):
                st.code(traceback.format_exc())
            st.info("Running heuristic fallback…")
            _run_heuristic_ui(data_dict, warehouse_cap, fixed_order, s)


def _run_heuristic_ui(data_dict, warehouse_cap, fixed_order, s):
    try:
        I, T, demand_df, I_ini, H, Area = read_input_data_from_dict(data_dict)
        policy_df, plan_df, obj_df, cap_df, total = _run_heuristic_fallback(
            I, T, demand_df, I_ini, H, Area, fixed_order, warehouse_cap)
        s.optimization_result = {
            "objective": total, "status": "heuristic (SCIP unavailable)",
            "policy_df": policy_df, "plan_df": plan_df,
            "obj_df": obj_df, "cap_df": cap_df,
        }
        st.rerun()
    except Exception as e:
        st.markdown(f'<div class="error-box">❌ Heuristic failed: {e}</div>', unsafe_allow_html=True)


def _render_results(s):
    res = s.optimization_result
    if not res:
        return

    policy_df = res.get("policy_df", pd.DataFrame())
    plan_df   = res.get("plan_df",   pd.DataFrame())
    obj_df    = res.get("obj_df",    pd.DataFrame())

    # ── Tokens ────────────────────────────────────────────────────────────────
    _CARD   = "#162535"; _CARD2  = "#1d3048"; _BORDER = "#243b55"
    _NAVY   = "#0d1b2a"; _NAVY2  = "#1a2e45"; _NAVY3  = "#243b55"
    _TEAL   = "#1bb8a0"; _ROSE   = "#e05c7a"; _AMBER  = "#f5a623"
    _SLATE2 = "#6b859e"; _WHITE  = "#f4f8fb"; _TEXT2  = "#a8c0d4"
    _TH = ("padding:9px 12px;font-size:10px;text-transform:uppercase;"
           "letter-spacing:.08em;color:#6b859e;font-weight:500;"
           "border-bottom:1px solid #243b55;white-space:nowrap;"
           "font-family:'DM Sans',sans-serif;background:#243b55;")
    _TD_SKU = ("padding:9px 12px;font-size:12px;color:#f4f8fb;"
               "border-bottom:1px solid #1a2e45;white-space:nowrap;"
               "font-family:'DM Mono',monospace;font-weight:500;")
    _TD_NUM = ("padding:9px 12px;font-size:12px;color:#a8c0d4;"
               "border-bottom:1px solid #1a2e45;white-space:nowrap;"
               "font-family:'DM Mono',monospace;text-align:right;")

    import plotly.graph_objects as go

    # ── Build selector options ─────────────────────────────────────────────────
    all_items = sorted(policy_df["Item"].unique().tolist()) if not policy_df.empty else []
    groups    = ["All Groups"] + sorted(set(str(i)[:3].upper() for i in all_items))

    # Reset SKU key when group changes
    prev_grp = s.get("_opt_prev_grp", None)
    curr_grp = s.get("opt_grp_sel", groups[0] if groups else "All Groups")
    if prev_grp != curr_grp:
        s["_opt_prev_grp"] = curr_grp
        if "opt_sku_sel" in st.session_state:
            del st.session_state["opt_sku_sel"]

    # ── Two-column outer layout ────────────────────────────────────────────────
    # CSS: make st.container(border=True) match sc-card design tokens exactly
    st.markdown(
        """<style>
        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #162535 !important;
            border: 1px solid #243b55 !important;
            border-radius: 10px !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"] label p {
            font-size: 10px !important;
            text-transform: uppercase !important;
            letter-spacing: 0.08em !important;
            color: #6b859e !important;
            font-weight: 500 !important;
            font-family: 'DM Sans', sans-serif !important;
        }
        </style>""",
        unsafe_allow_html=True,
    )

    _CHART_H = 340  # uniform chart height for both columns

    # ══ ROW 1: Optimization Parameters (left) | 3 KPI Tiles (right) ══════════
    row1_l, row1_r = st.columns([9, 11], gap="large")

    with row1_l:
        with st.container(border=True):
            st.markdown(
                '<p style="font-family:Fraunces,Georgia,serif;font-weight:300;'
                'font-size:18px;color:#f4f8fb;margin:0 0 4px 0;">'
                'Optimization Parameters</p>'
                '<p style="font-size:12px;color:#6b859e;margin:0 0 16px 0;">'
                'Set cost and service level parameters</p>',
                unsafe_allow_html=True,
            )
            cg, cs = st.columns([1, 2])
            with cg:
                grp_sel = st.selectbox("PRODUCT GROUP", groups, key="opt_grp_sel")
            with cs:
                items_in_grp = (
                    [i for i in all_items if str(i).upper().startswith(grp_sel)]
                    if grp_sel != "All Groups" else all_items
                )
                sku_display = [f"{i} ({str(i)[:3].upper()})" for i in items_in_grp]
                sku_sel_lbl = st.selectbox(
                    "SKU", sku_display if sku_display else ["— no items —"],
                    key="opt_sku_sel", index=0,
                )

    sel_item = (
        items_in_grp[sku_display.index(sku_sel_lbl)]
        if sku_display and sku_sel_lbl != "— no items —" else None
    )

    # Pre-compute all SKU metrics before row1_r and row2 so both cols can use them
    if sel_item and not policy_df.empty and not plan_df.empty:
        pol_row   = policy_df[policy_df["Item"] == sel_item]
        pln_sku   = plan_df[plan_df["Item"] == sel_item]
        s_val     = float(pol_row["s_i"].values[0]) if not pol_row.empty else 0.0
        S_val     = float(pol_row["S_i"].values[0]) if not pol_row.empty else 0.0
        avg_inv   = float(((pln_sku["Prev_Inventory"] + pln_sku["I_it_End"]) / 2).mean()) if not pln_sku.empty else 0.0
        all_avg   = float(((plan_df["Prev_Inventory"] + plan_df["I_it_End"]) / 2).mean()) if not plan_df.empty else 1.0
        sku_frac  = avg_inv / max(all_avg * len(policy_df), 0.001)
        rows_obj  = {r["Objective Component"]: r["Value"] for _, r in obj_df.iterrows()} if not obj_df.empty else {}
        holding_sku  = round(rows_obj.get("Z1: Warehouse Holding Cost", 0) * sku_frac, 2)
        ordering_sku = round(rows_obj.get("Z2: Fixed Production Cost",  0) * sku_frac, 2)
        total_annual = round(holding_sku + ordering_sku, 2)
        orders_placed = int(pln_sku["B_it"].sum())
        n_periods     = len(pln_sku)
        orders_per_yr = round((orders_placed / max(n_periods, 1)) * 12, 1)
        total_produced = round(float(pln_sku["Q_it"].sum()), 0)
        has_sku_data  = True
    else:
        s_val = S_val = total_annual = 0.0
        holding_sku = ordering_sku = 0.0
        pln_sku = pd.DataFrame()
        has_sku_data = False

    def _kpi(label, value, sub):
        DMS = "DM Sans"; DMM = "DM Mono"
        return (
            f'<div style="flex:1;background:#1d3048;border:1px solid #243b55;'
            f'border-radius:8px;padding:16px 12px;text-align:center;min-width:0;'
            f'min-height:110px;display:flex;flex-direction:column;justify-content:center;">'
            f'<div style="font-size:9px;text-transform:uppercase;letter-spacing:.1em;'
            f'color:#6b859e;font-family:{DMS!r};margin-bottom:8px;">{label}</div>'
            f'<div style="font-family:{DMM!r};font-size:26px;'
            f'color:#1bb8a0;line-height:1.1;">{value}</div>'
            f'<div style="font-size:11px;color:#8fa3b8;margin-top:5px;">{sub}</div>'
            f"</div>"
        )

    with row1_r:
        if has_sku_data:
            st.markdown(
                '<div style="display:flex;gap:10px;">' +
                _kpi("REORDER POINT (MIN)", f"{s_val:,.0f}",       "units") +
                _kpi("ORDER-UPTO (MAX)",    f"{S_val:,.0f}",       "units") +
                _kpi("TOTAL ANNUAL COST",   f"${total_annual:,.0f}", "$ / year") +
                '</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ══ ROW 2: Inventory Level Simulation (left) | Cost Breakdown (right) ═════
    row2_l, row2_r = st.columns([9, 11], gap="large")

    with row2_l:
        if has_sku_data and not pln_sku.empty:
            # ── Resolve YYYY-MM period labels ──────────────────────────────────
            fc_input = s.get("forecast_input_dict")
            ym_map   = fc_input.get("ym_map",   {}) if fc_input else {}
            ym_order = fc_input.get("ym_order", []) if fc_input else []

            if ym_order:
                sort_key = {p: i for i, p in enumerate(ym_order)}
                pln_sku  = pln_sku.copy()
                pln_sku["_sort"] = pln_sku["Period"].map(
                    lambda p: sort_key.get(int(p), 999))
                pln_sku  = pln_sku.sort_values("_sort").drop(
                    columns=["_sort"]).reset_index(drop=True)

            def _lbl(p):
                return ym_map.get(int(p), str(int(p))) if ym_map else str(int(p))

            per_labels = [_lbl(p) for p in pln_sku["Period"].tolist()]
            inv_open   = pln_sku["Prev_Inventory"].tolist()
            inv_end    = pln_sku["I_it_End"].tolist()
            b_it       = pln_sku["B_it"].tolist()
            q_it       = pln_sku["Q_it"].tolist()

            # ── Design ─────────────────────────────────────────────────────────
            # Each period has 3 sub-x positions:
            #   lbl__a  = opening inventory  (before order)
            #   lbl__b  = post-order level   (= open + Q_it)  ← same x as __a
            #   lbl__c  = ending inventory   (after demand)
            #
            # Using the SAME x for __a and __b makes the open→post segment
            # perfectly vertical — showing the order as instant, not gradual.
            #
            # The teal line traces the full path: open→post→end each period.
            # The amber Q_it overlay traces ONLY the open→post vertical segment,
            # drawn as a thicker line on top so it looks like the teal line
            # itself shows the restock jump in amber.

            x_main, y_main, hover_main = [], [], []   # full teal inventory path
            x_qit,  y_qit,  hover_qit = [], [], []   # amber vertical Q_it segments
            x_dots, y_dots = [], []
            dot_col, dot_sz, dot_sym = [], [], []

            for idx, lbl in enumerate(per_labels):
                open_v = float(inv_open[idx])
                end_v  = float(inv_end[idx])
                q_v    = float(q_it[idx])
                is_ord = bool(b_it[idx])
                post_v = open_v + q_v            # post-restock level

                xa = lbl + "__a"   # opening  — shared by spike bottom too
                xb = lbl + "__a"   # post      — SAME x as xa → vertical line
                xc = lbl + "__c"   # ending

                # Full inventory path
                x_main += [xa, xb, xc]
                y_main += [open_v, post_v, end_v]
                hover_main += [
                    f"<b>{lbl}</b><br>📦 Opening Inv: {open_v:.2f} units",
                    (f"<b>{lbl}</b><br>⚡ After restock: {post_v:.2f} units"
                     f"<br>Production Q_it: +{q_v:.2f}"
                     if is_ord else f"<b>{lbl}</b><br>No order this period"),
                    f"<b>{lbl}</b><br>📉 Ending Inv: {end_v:.2f} units",
                ]

                # Amber Q_it segment — vertical (xa == xb), drawn over the teal line
                if is_ord and q_v > 0:
                    x_qit += [xa, xb, None]
                    y_qit += [open_v, post_v, None]
                    hover_qit += [
                        f"<b>{lbl}</b><br>⚡ Production Q_it: {q_v:.2f} units",
                        f"<b>{lbl}</b><br>⚡ Production Q_it: {q_v:.2f} units",
                        "",
                    ]

                # Dot at opening — amber open-circle on order periods
                x_dots.append(xa)
                y_dots.append(open_v)
                dot_col.append(_AMBER if is_ord else _TEAL)
                dot_sz.append(10 if is_ord else 5)
                dot_sym.append("circle-open" if is_ord else "circle")

            # One tick per period at __a position
            x_tick_vals = [lbl + "__a" for lbl in per_labels]
            x_tick_text = per_labels
            y_max = max(y_main + [S_val, s_val], default=100) * 1.15

            fig_sim = go.Figure()

            # Fill under teal line
            fig_sim.add_trace(go.Scatter(
                x=x_main, y=y_main, mode="none", fill="tozeroy",
                fillcolor="rgba(27,184,160,0.07)", showlegend=False, hoverinfo="skip",
            ))

            # Teal inventory line — full path including vertical jumps
            fig_sim.add_trace(go.Scatter(
                x=x_main, y=y_main, mode="lines", name="Inventory Level",
                line=dict(color=_TEAL, width=2.5, shape="linear"),
                text=hover_main, hovertemplate="%{text}<extra></extra>",
            ))

            # Amber Q_it overlay — same vertical segment, thicker, drawn on top
            # Appears as part of the inventory line itself, coloured amber at jump
            if x_qit:
                fig_sim.add_trace(go.Scatter(
                    x=x_qit, y=y_qit, mode="lines", name="Production Q_it",
                    line=dict(color=_AMBER, width=4, shape="linear"),
                    text=hover_qit, hovertemplate="%{text}<extra></extra>",
                ))

            # Dot markers
            fig_sim.add_trace(go.Scatter(
                x=x_dots, y=y_dots, mode="markers", showlegend=False,
                marker=dict(size=dot_sz, color=dot_col, symbol=dot_sym,
                            line=dict(width=2, color=dot_col)),
                hoverinfo="skip",
            ))

            # S line — Order-Up-To (amber dashed)
            fig_sim.add_trace(go.Scatter(
                x=x_main, y=[S_val]*len(x_main), mode="lines",
                name=f"Order-Up-To S ({S_val:,.1f})",
                line=dict(color=_AMBER, width=1.5, dash="dash"),
                hovertemplate=f"Order-Up-To (S): {S_val:.1f}<extra></extra>",
            ))

            # s line — Reorder Point (rose dashed)
            fig_sim.add_trace(go.Scatter(
                x=x_main, y=[s_val]*len(x_main), mode="lines",
                name=f"Reorder Point s ({s_val:,.1f})",
                line=dict(color=_ROSE, width=1.5, dash="dash"),
                hovertemplate=f"Reorder Point (s): {s_val:.1f}<extra></extra>",
            ))

            fig_sim.update_layout(
                paper_bgcolor=_CARD, plot_bgcolor=_CARD2, height=_CHART_H,
                title=dict(
                    text='<span style="font-family:Fraunces,Georgia,serif;font-weight:300;'
                         'font-size:15px;color:#f4f8fb;">Inventory Level — (s,S) Policy</span>',
                    x=0.0, y=0.99, xanchor="left", yanchor="top",
                ),
                font=dict(family="DM Sans, sans-serif", color=_TEXT2, size=11),
                margin=dict(l=50, r=20, t=45, b=55),
                xaxis=dict(
                    gridcolor=_NAVY3, linecolor=_NAVY3, zeroline=False,
                    showgrid=True, tickfont=dict(color=_SLATE2, size=9), tickangle=-30,
                    tickvals=x_tick_vals, ticktext=x_tick_text,
                ),
                yaxis=dict(
                    gridcolor=_NAVY3, linecolor=_NAVY3, zeroline=False,
                    showgrid=True, tickfont=dict(color=_SLATE2, size=9),
                    range=[0, y_max],
                    title=dict(text="Units", font=dict(color=_SLATE2, size=10)),
                ),
                legend=dict(orientation="h", y=-0.22, x=0.5, xanchor="center",
                            bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
                            font=dict(size=10, color=_TEXT2), itemsizing="constant"),
                hoverlabel=dict(bgcolor=_NAVY2, bordercolor=_BORDER,
                                font=dict(family="DM Sans, sans-serif", color=_WHITE, size=12)),
                hovermode="closest",
                annotations=[dict(
                    text="period-by-period projection with (s,S) trigger",
                    x=1.0, y=1.04, xref="paper", yref="paper", showarrow=False,
                    font=dict(color=_SLATE2, size=9, family="DM Sans, sans-serif"),
                    xanchor="right",
                )],
            )
            st.plotly_chart(fig_sim, use_container_width=True, config={"displayModeBar": False})

    with row2_r:
        if has_sku_data:
            # Use aggregate totals from obj_df (Objective_Breakdown sheet)
            # These are the exact Z1 and Z2 totals across ALL selected SKUs
            rows_obj_all  = {r["Objective Component"]: r["Value"]
                             for _, r in obj_df.iterrows()} if not obj_df.empty else {}
            z1_total      = round(rows_obj_all.get("Z1: Warehouse Holding Cost", 0), 2)
            z2_total      = round(rows_obj_all.get("Z2: Fixed Production Cost",  0), 2)
            donut_vals    = [max(z2_total, 0), max(z1_total, 0)]
            donut_labels  = ["Ordering Cost", "Inventory Cost"]
            donut_colors  = [_AMBER, _TEAL]
            z_total       = z1_total + z2_total

            fig_donut = go.Figure(go.Pie(
                labels=donut_labels, values=donut_vals, hole=0.55,
                marker=dict(colors=donut_colors, line=dict(color=_CARD, width=3)),
                # Show % inside each slice like the reference screenshot
                textinfo="percent",
                textfont=dict(size=13, color=_WHITE, family="DM Sans, sans-serif"),
                insidetextorientation="horizontal",
                sort=False, direction="clockwise",
                hovertemplate="<b>%{label}</b><br>$%{value:,.2f} (%{percent})<extra></extra>",
            ))

            # Centre annotation showing total value + "Total" label
            fig_donut.add_annotation(
                text=f"<b>${z_total:,.0f}</b><br><span style='font-size:11px'>Total</span>",
                x=0.5, y=0.5, xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=18, color=_WHITE, family="DM Mono, monospace"),
                align="center",
            )

            fig_donut.update_layout(
                paper_bgcolor=_CARD, plot_bgcolor=_CARD, height=_CHART_H,
                title=dict(
                    text='<span style="font-family:Fraunces,Georgia,serif;font-weight:300;font-size:15px;color:#f4f8fb;">Cost Breakdown</span>',
                    font=dict(family="Fraunces, Georgia, serif", size=15, color=_WHITE),
                    x=0.0, y=0.99, xanchor="left", yanchor="top",
                ),
                font=dict(family="DM Sans, sans-serif", color=_TEXT2, size=11),
                margin=dict(l=10, r=120, t=40, b=40),
                legend=dict(
                    orientation="h", x=0.5, y=-0.05,
                    xanchor="center", yanchor="top",
                    bgcolor="rgba(0,0,0,0)",
                    font=dict(size=11, color=_TEXT2),
                ),
                hoverlabel=dict(bgcolor=_NAVY2, bordercolor=_BORDER,
                                font=dict(family="DM Sans, sans-serif", color=_WHITE, size=12)),
            )
            st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})
        else:
            rows_agg = {r["Objective Component"]: r["Value"]
                        for _, r in obj_df.iterrows()} if not obj_df.empty else {}
            st.markdown(f"""
            <div style="flex:1;background:#1d3048;border:1px solid #243b55;border-radius:8px;
                        padding:16px;text-align:center;">
              <div style="font-size:9px;text-transform:uppercase;color:#6b859e;">Total Objective</div>
              <div style="font-size:24px;color:#1bb8a0;font-family:'DM Mono',monospace;">
                  ${res['objective']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)

    # Policy table — title + subtitle + table all in one markdown call
    tbl_policy = policy_df  # always show all SKUs regardless of selector
    if not tbl_policy.empty:
        col_map = {"Item": "Item", "s_i": "Reorder Point s", "S_i": "Order-Up-To S"}
        avail = [c for c in col_map if c in tbl_policy.columns]

        # Column filter
        pol_f1, pol_f2 = st.columns([3, 1])
        with pol_f1:
            pol_flt_item = st.text_input("Item", placeholder="Search item…", key="pol_flt_item", label_visibility="collapsed")
        with pol_f2:
            pol_reset = st.button("🔄 Reset", key="pol_flt_reset", use_container_width=True)
        tbl_policy_f = tbl_policy.copy()
        if pol_flt_item:
            tbl_policy_f = tbl_policy_f[tbl_policy_f["Item"].str.contains(pol_flt_item, case=False, na=False)]

        total_policy = len(tbl_policy_f)
        rows_html = ""
        for _, row in tbl_policy_f[avail].iterrows():
            cells = ""
            for c in avail:
                val = row[c]
                cells += (f'<td style="{_TD_SKU}">{val}</td>' if c == "Item"
                          else f'<td style="{_TD_NUM}">{float(val):.4f}</td>')
            rows_html += f'<tr style="border-left:3px solid transparent;">{cells}</tr>'
        st.markdown(
            '<div class="sc-card">'
            '<div class="sc-card-title" style="margin-bottom:4px">📋 (s,S) Reorder Policy Levels</div>'
            '<div class="sc-card-sub" style="margin-bottom:14px">Order when Opening Inventory ≤ s; order up to S</div>'
            '<div style="overflow-x:auto;overflow-y:auto;max-height:400px;">'
            '<table style="width:100%;border-collapse:collapse;background:#1d3048;border-radius:8px;overflow:hidden;">'
            f'<thead><tr style="background:#243b55;">'
            + "".join(f'<th style="{_TH}">{col_map[c]}</th>' for c in avail)
            + f'</tr></thead><tbody>{rows_html}</tbody></table></div>'
            + f'<div style="font-size:11px;color:#6b859e;margin-top:10px;">'
              f'{total_policy:,} items</div></div>',
            unsafe_allow_html=True,
        )

    # Period plan table — title + subtitle + table all in one markdown call
    if not plan_df.empty:
        tbl_plan = plan_df.copy()  # always show all SKUs regardless of selector

        # Column filters for plan table
        pl_f1, pl_f2, pl_f3 = st.columns([3, 1, 1])
        with pl_f1:
            pl_flt_item = st.text_input("Item filter", placeholder="Search item…", key="pl_flt_item", label_visibility="collapsed")
        with pl_f2:
            all_periods = sorted(tbl_plan["Period"].unique().tolist())
            period_opts = ["All"] + [str(p) for p in all_periods]
            pl_flt_per  = st.selectbox("Period", period_opts, key="pl_flt_per", label_visibility="collapsed")
        with pl_f3:
            pl_reset = st.button("🔄 Reset", key="pl_flt_reset", use_container_width=True)
        if pl_flt_item:
            tbl_plan = tbl_plan[tbl_plan["Item"].str.contains(pl_flt_item, case=False, na=False)]
        if pl_flt_per != "All":
            tbl_plan = tbl_plan[tbl_plan["Period"].astype(str) == pl_flt_per]

        total_plan = len(tbl_plan)

        # ── Build Period → "YYYY-MM" label ─────────────────────────────────────
        # ym_map keys are actual month numbers: {12: "2025-12", 1: "2026-01", 2: "2026-02"}
        # ym_order is the chronological list: [12, 1, 2]
        fc_input = s.get("forecast_input_dict")
        ym_map   = fc_input.get("ym_map",   {}) if fc_input is not None else {}
        ym_order = fc_input.get("ym_order", []) if fc_input is not None else []

        period_label_map = {}
        if ym_map:
            # Map each period (month number) directly to its YYYY-MM label
            for p in tbl_plan["Period"].unique():
                period_label_map[int(p)] = ym_map.get(int(p), str(int(p)))
        else:
            # Fallback: use forecast detail_df
            fc_res    = s.get("forecast_result")
            detail_df = fc_res.get("detail_df") if fc_res is not None else None
            if detail_df is not None and not detail_df.empty:
                fc_rows = (detail_df[detail_df["Demand_Prediction"].notna()]
                           [["Year","Month"]].drop_duplicates()
                           .sort_values(["Year","Month"]).reset_index(drop=True))
                for _, row in fc_rows.iterrows():
                    mo = int(row["Month"])
                    yr = int(row["Year"])
                    period_label_map[mo] = f"{yr}-{mo:02d}"
            for p in tbl_plan["Period"].unique():
                if int(p) not in period_label_map:
                    period_label_map[int(p)] = str(int(p))

        # Sort tbl_plan rows chronologically using ym_order
        # ym_order = [12, 1, 2] means Dec comes first, then Jan, then Feb
        if ym_order:
            period_sort_key = {p: i for i, p in enumerate(ym_order)}
            tbl_plan["_sort"] = tbl_plan["Period"].map(
                lambda p: period_sort_key.get(int(p), 999))
            tbl_plan = tbl_plan.sort_values(["Item", "_sort"]).drop(columns=["_sort"])
            tbl_plan = tbl_plan.reset_index(drop=True)

        # Split Period into separate Year and Month columns using period_label_map
        # period_label_map: {12: "2025-12", 1: "2026-01", 2: "2026-02"}
        # Safe split: if label has no "-" (fallback is just the period number), use "N/A"
        def _safe_year(p):
            label = period_label_map.get(int(p), "")
            parts = label.split("-")
            return parts[0] if len(parts) >= 2 else str(int(p))

        def _safe_month(p):
            label = period_label_map.get(int(p), "")
            parts = label.split("-")
            return parts[1] if len(parts) >= 2 else str(int(p))

        tbl_plan["Year"]  = tbl_plan["Period"].map(_safe_year)
        tbl_plan["Month"] = tbl_plan["Period"].map(_safe_month)
        tbl_plan = tbl_plan.drop(columns=["Period"])

        # Column display names — Year and Month as separate columns
        col_display = {
            "Item":             "Item",
            "Year":             "Year",
            "Month":            "Month",
            "Prev_Inventory":   "Opening Inventory",
            "Q_it":             "Production/Order Quantity",
            "D_it":             "Predicted Demand",
            "I_it_End":         "Ending Inventory",
            "Area_m2_per_item": "Area m²/Unit",
            "Used_Area_m2":     "Used Area m²",
        }
        display_cols = [c for c in col_display if c in tbl_plan.columns]

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        plan_rows_html = ""
        for _, row in tbl_plan[display_cols].iterrows():
            cells = ""
            for c in display_cols:
                val = row[c]
                if c == "Item":
                    cells += f'<td style="{_TD_SKU}">{val}</td>'
                elif c in ("Year", "Month"):
                    cells += f'<td style="{_TD_NUM}font-family:DM Mono,monospace;">{val}</td>'
                elif c == "Q_it":
                    cells += f'<td style="{_TD_NUM}">{float(val):.2f}</td>'
                elif isinstance(val, float):
                    cells += f'<td style="{_TD_NUM}">{val:.2f}</td>'
                else:
                    cells += f'<td style="{_TD_NUM}">{val}</td>'
            plan_rows_html += f'<tr style="border-left:3px solid transparent;">{cells}</tr>'

        # Sticky header fix: wrap table in a div with overflow, thead with sticky+z-index
        # The extra padding-top on tbody compensates so first row isn't hidden behind sticky header
        st.markdown(
            '<div class="sc-card">'
            '<div class="sc-card-title" style="margin-bottom:4px">📋 Full Period-by-Period Plan</div>'
            '<div class="sc-card-sub" style="margin-bottom:14px">Inventory, orders and shortages by item and period</div>'
            '<div style="overflow-x:auto;overflow-y:auto;max-height:460px;border-radius:6px;">'
            '<table style="width:100%;border-collapse:collapse;background:#1d3048;min-width:1100px;">'
            '<thead><tr style="background:#243b55;position:sticky;top:0;z-index:10;box-shadow:0 2px 4px rgba(0,0,0,0.4);">'
            + "".join(f'<th style="{_TH}">{col_display[c]}</th>' for c in display_cols)
            + f'</tr></thead><tbody>{plan_rows_html}</tbody></table></div>'
            + f'<div style="font-size:11px;color:#6b859e;margin-top:10px;">'
              f'{len(tbl_plan):,} rows — scroll horizontally and vertically</div></div>',
            unsafe_allow_html=True,
        )

    # Download — Period_Results uses the same transformed table shown in UI
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="sc-card">'
                '<div class="sc-card-title">💾 Export Results</div>',
                unsafe_allow_html=True)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        if not policy_df.empty:
            policy_df.to_excel(w, sheet_name="Policy_Levels", index=False)

        # Period_Results: same columns and labels as the Full Period-by-Period Plan UI table
        if not plan_df.empty:
            ep = plan_df.copy()

            # Apply Year/Month split using ym_map from forecast input
            fc_inp   = s.get("forecast_input_dict")
            ym_map_e = fc_inp.get("ym_map",   {}) if fc_inp is not None else {}
            ym_ord_e = fc_inp.get("ym_order", []) if fc_inp is not None else []

            def _ey(p):
                lbl = ym_map_e.get(int(p), ""); parts = lbl.split("-")
                return parts[0] if len(parts) >= 2 else str(int(p))
            def _em(p):
                lbl = ym_map_e.get(int(p), ""); parts = lbl.split("-")
                return parts[1] if len(parts) >= 2 else str(int(p))

            ep.insert(ep.columns.get_loc("Period"),     "Year",  ep["Period"].map(_ey))
            ep.insert(ep.columns.get_loc("Year") + 1,  "Month", ep["Period"].map(_em))
            ep = ep.drop(columns=["Period"])

            # Sort chronologically by ym_order
            if ym_ord_e:
                sk = {p: i for i, p in enumerate(ym_ord_e)}
                ep["_s"] = ep["Month"].apply(lambda m: sk.get(int(m) if str(m).isdigit() else 0, 999))
                ep = ep.sort_values(["Item", "_s"]).drop(columns=["_s"])

            # Rename to match UI display names (same as col_display in table)
            ecm = {
                "Item":             "Item",
                "Year":             "Year",
                "Month":            "Month",
                "Prev_Inventory":   "Opening Inventory",
                "Q_it":             "Production/Order Quantity",
                "D_it":             "Predicted Demand",
                "I_it_End":         "Ending Inventory",
                "Area_m2_per_item": "Area m²/Unit",
                "Used_Area_m2":     "Used Area m²",
            }
            ec = [c for c in ecm if c in ep.columns]
            ep = ep[ec].rename(columns=ecm).reset_index(drop=True)
            ep.to_excel(w, sheet_name="Period_Results", index=False)

        if not obj_df.empty:
            obj_df.to_excel(w, sheet_name="Objective_Breakdown", index=False)

    st.download_button("⬇️ Download Results (.xlsx)", data=buf.getvalue(),
                       file_name="KleenTex_Optimization_Results.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.markdown("</div>", unsafe_allow_html=True)


def _load_opt_input_from_file(uploaded_file) -> dict:
    """Load optimization input from user-uploaded Excel (same format as Input_Data_Adjusted.py output)."""
    xls        = pd.ExcelFile(uploaded_file)
    demand_raw = pd.read_excel(xls, sheet_name="Demand",        header=None)
    T = demand_raw.iloc[1, 1:].tolist()
    I = demand_raw.iloc[2:, 0].tolist()
    demand_df          = demand_raw.iloc[2:, 1:].copy()
    demand_df.columns  = T
    demand_df.index    = I
    demand_df          = demand_df.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    demand_pivot       = demand_df.reset_index().rename(columns={"index": "Item No."})

    iini_raw     = pd.read_excel(xls, sheet_name="I_ini", header=None)
    iini_df      = iini_raw.iloc[1:].copy()
    iini_df.columns = ["Item No.", "Opening_Inventory_Qty"]

    inv_cost = pd.read_excel(xls, sheet_name="Inventory Cost")
    m2_df    = pd.read_excel(xls, sheet_name="m2 per item")

    return {"demand_pivot": demand_pivot, "initial_inventory": iini_df,
            "inventory_cost": inv_cost, "m2_per_item": m2_df}
