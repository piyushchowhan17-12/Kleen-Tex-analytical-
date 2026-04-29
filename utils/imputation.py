"""
Imputation logic — exact port of Imputation_Output_logic_Fix.py
for use inside the Streamlit dashboard (operates on DataFrames in memory).
"""

import numpy as np
import pandas as pd


def impute_demand(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply professor's imputation logic to a single DataFrame.
    Exact copy of impute_demand_logic() from Imputation_Output_logic_Fix.py.

    Rules:
    - If Monthly_QTY == 0 and the PREVIOUS period's Ending_Inventory_Qty == 0
      → treat as missing and linearly interpolate.
    - Otherwise keep Monthly_QTY as is.
    - Only internal gaps are interpolated (limit_area='inside').
    - New column 'Imputed_Demand' is added.
    """
    df = df.copy()

    # Rename 'Item No.' → 'SKU' if needed (from original 2A)
    if "Item No." in df.columns and "SKU" not in df.columns:
        df = df.rename(columns={"Item No.": "SKU"})

    required = ["SKU", "Year", "Month", "Monthly_QTY", "Opening_Inventory_Qty", "Ending_Inventory_Qty"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"These required columns are missing: {missing}")

    # 2B — sort in time order (from original)
    df = df.sort_values(["SKU", "Year", "Month"]).reset_index(drop=True)

    # Start with original values
    df["Imputed_Demand"] = df["Monthly_QTY"]

    # 2C — get previous month's ending inventory per SKU (from original)
    df["Prev_Ending_Inventory_Qty"] = (
        df.groupby("SKU")["Ending_Inventory_Qty"].shift(1)
    )

    # 2D — identify zero-demand rows to impute (from original)
    impute_mask = (
        (df["Monthly_QTY"] == 0) &
        (df["Prev_Ending_Inventory_Qty"] == 0)
    )
    df.loc[impute_mask, "Imputed_Demand"] = np.nan

    # 2E — interpolate within each SKU (from original)
    df["Imputed_Demand"] = (
        df.groupby("SKU")["Imputed_Demand"]
          .transform(lambda s: s.interpolate(method="linear", limit_area="inside"))
    )

    # 2F — fill remaining NaN with original Monthly_QTY (from original)
    df["Imputed_Demand"] = df["Imputed_Demand"].fillna(df["Monthly_QTY"])

    # Drop helper column (from original)
    df = df.drop(columns=["Prev_Ending_Inventory_Qty"])

    return df


def compute_sku_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-SKU statistics: ADI, CV², demand type, nonzero periods, etc.
    Uses Imputed_Demand if present, else Monthly_QTY.
    Only uses historical rows (Monthly_QTY not NaN) to avoid pollution from
    appended forecast rows.
    """
    demand_col = "Imputed_Demand" if "Imputed_Demand" in df.columns else "Monthly_QTY"

    # Filter to historical rows only — forecast rows have NaN Monthly_QTY
    hist_df = df[df["Monthly_QTY"].notna()].copy() if "Monthly_QTY" in df.columns else df.copy()

    records = []
    for sku, grp in hist_df.groupby("SKU"):
        vals    = grp[demand_col].dropna().astype(float).values
        n       = len(vals)
        nonzero = int(np.sum(vals > 0))

        if nonzero == 0:
            adi   = 9999.0
            cv2   = 9999.0
            dtype = "insufficient"
        else:
            adi      = n / nonzero
            pos_vals = vals[vals > 0]
            cv2      = float((np.std(pos_vals) / np.mean(pos_vals)) ** 2) if len(pos_vals) > 1 else 0.0
            if n < 8 or nonzero < 4:
                dtype = "insufficient"
            elif np.mean(vals == 0) >= 0.50:
                dtype = "intermittent"
            elif cv2 > 1.0:
                dtype = "erratic"
            else:
                dtype = "smooth"

        group = _infer_group(str(sku))

        records.append({
            "SKU":             sku,
            "Group":           group,
            "ADI":             round(adi, 4) if np.isfinite(adi) else 9999.0,
            "CV2":             round(cv2, 4) if np.isfinite(cv2) else 9999.0,
            "Nonzero_Periods": nonzero,
            "Total_Periods":   n,
            "Mean_Demand":     round(float(np.mean(vals)), 2),
            "Std_Demand":      round(float(np.std(vals)), 2),
            "Demand_Type":     dtype,
            "pass_filter":     False,
        })

    return pd.DataFrame(records)


def apply_thresholds(stats_df: pd.DataFrame, adi_thresh: float, cv2_thresh: float) -> pd.DataFrame:
    df = stats_df.copy()
    df["pass_filter"] = (df["ADI"] <= adi_thresh) & (df["CV2"] <= cv2_thresh)
    return df


def _infer_group(sku: str) -> str:
    if len(sku) >= 3:
        return sku[:3].upper()
    return "UNK"


def get_imputation_summary(original_df: pd.DataFrame, imputed_df: pd.DataFrame) -> dict:
    """
    Return high-level imputation statistics.
    Robust to shape mismatches: imputed_df may have extra forecast rows appended
    by the forecasting pipeline (those rows have NaN Monthly_QTY).
    We align by SKU+Year+Month before comparing so row counts never mismatch.
    """
    demand_col_orig = "Monthly_QTY"
    demand_col_imp  = "Imputed_Demand"

    orig_zeros = int((original_df[demand_col_orig] == 0).sum())

    # Align on SKU + Year + Month to safely compare regardless of shape
    key_cols = ["SKU", "Year", "Month"]
    orig_ok  = all(c in original_df.columns for c in key_cols)
    imp_ok   = all(c in imputed_df.columns  for c in key_cols)

    if orig_ok and imp_ok and demand_col_imp in imputed_df.columns:
        # Only keep historical rows from imputed_df (Monthly_QTY not NaN)
        imp_hist = imputed_df[imputed_df[demand_col_orig].notna()].copy() \
                   if demand_col_orig in imputed_df.columns \
                   else imputed_df.copy()

        orig_keyed = original_df[key_cols + [demand_col_orig]].copy()
        imp_keyed  = imp_hist[key_cols + [demand_col_imp]].copy()
        merged     = orig_keyed.merge(imp_keyed, on=key_cols, how="inner")
        changed    = int(
            ((merged[demand_col_orig] == 0) & (merged[demand_col_imp] != 0)).sum()
        )
    else:
        # Fallback: compare up to the shorter length
        n       = min(len(original_df), len(imputed_df))
        changed = int((
            (original_df[demand_col_orig].values[:n] == 0) &
            (imputed_df[demand_col_imp].values[:n]   != 0)
        ).sum()) if demand_col_imp in imputed_df.columns else 0

    sku_col = "SKU" if "SKU" in original_df.columns else "Item No."
    return {
        "total_rows":       len(original_df),
        "unique_skus":      original_df[sku_col].nunique(),
        "zero_demand_rows": orig_zeros,
        "imputed_rows":     changed,
        "imputation_pct":   round(changed / max(orig_zeros, 1) * 100, 1),
    }
