"""Session state initialization and helpers."""

import streamlit as st


def init_session():
    defaults = {
        "active_module":        "preprocess",
        "raw_data":             None,   # pd.DataFrame
        "raw_filename":         None,
        "selected_skus":        None,   # list[str]
        "n_skus":               5,
        "imputed_data":         None,   # pd.DataFrame
        "forecast_result":      None,   # pd.DataFrame  (Forecast_Detail)
        "forecast_summary":     None,   # pd.DataFrame  (Model_Summary)
        "forecast_fold_df":     None,   # pd.DataFrame  (Fold_Summary)
        "forecast_input_df":    None,   # dict of DataFrames for optimizer
        "forecast_input_ready": False,
        "optimization_result":  None,   # dict of DataFrames
        "opt_policy_df":        None,
        "opt_plan_df":          None,
        "opt_obj_df":           None,
        "opt_cap_df":           None,
        # forecasting params
        "adi_threshold":        1.32,
        "cv2_threshold":        0.49,
        "forecast_months":      3,
        # optimization params
        "warehouse_capacity":   500_000.0,
        "fixed_order_cost":     500.0,
        "shortage_cost":        50.0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
