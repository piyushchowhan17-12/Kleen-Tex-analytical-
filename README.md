# Supply Chain Analytics Dashboard

End-to-end supply chain demand forecasting and inventory optimization platform built with Streamlit.

## Features

| Module | Description |
|--------|-------------|
| 📥 Data Upload | Upload raw Excel data, select SKUs for pipeline |
| 🧹 Preprocessing & Imputation | Professor's logic: zero demand + prior stockout → linear interpolation |
| 📈 Demand Forecasting | RF 2-Stage, SARIMA, TSB, Seasonal Naïve with rolling validation |
| ⚙️ Optimization | (s,S) policy via SCIP solver — minimize holding + setup + shortage cost |

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note on SCIP:** `pyscipopt` requires the SCIP binary installed on your system.
> Download from [scip-optimization.com](https://www.scipopt.org/index.php#download).
> If SCIP is not available, the optimization module falls back to a heuristic (s,S) policy.

### 2. Run the Dashboard

```bash
streamlit run app.py
```

### 3. Deploy on Streamlit Cloud

1. Push this folder to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo → set **Main file path** to `app.py`
4. Add any secrets via the Streamlit Cloud secrets manager

> **Cloud note:** PySCIPOpt may not be available on Streamlit Cloud's free tier.
> The dashboard detects this automatically and uses the heuristic fallback.

## Required Input Data Format

Your Excel file must contain a sheet with these columns:

| Column | Type | Description |
|--------|------|-------------|
| `Item No.` or `SKU` | string | Product identifier |
| `Year` | int | Calendar year |
| `Month` | int | Month number (1–12) |
| `Monthly_QTY` | float | Sales quantity |
| `Opening_Inventory_Qty` | float | Opening stock |
| `Ending_Inventory_Qty` | float | Closing stock |

## Pipeline Overview

```
Raw Data Upload
      │
      ▼
SKU Selection (Top N / Manual)
      │
      ▼
Module 1: Preprocessing & Imputation
  • Professor's logic: zero demand + prior stockout → interpolate
  • ADI / CV² classification & threshold filtering
      │
      ▼
Module 2: Demand Forecasting
  • ADI = total periods / nonzero periods
  • CV² = (std/mean)² of positive demand values
  • Models: RandomForest 2-Stage, SARIMA, TSB, Seasonal Naïve, Moving Average
  • Rolling 3-fold cross-validation for model selection
  • Generates N months of future forecasts
      │
      ▼
Optimization Input Builder
  • Converts forecasts → Demand sheet + I_ini + Inventory Cost + m2 per item
  • Downloadable as Input_Data_Adjusted.xlsx
      │
      ▼
Module 3: Inventory Optimization
  • (s,S) policy: reorder when I_Open ≤ s, order up to S
  • Objective: Min Z₁ (holding) + Z₂ (setup) + Z₃ (shortage)
  • Warehouse capacity constraint: Σ area_i × (I_Open + Q) ≤ C
      │
      ▼
Results Export (Excel)
```

## File Structure

```
dashboard/
├── app.py                      # Streamlit entry point
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml             # Theme + server config
├── modules/
│   ├── upload.py               # Module 0: Data Upload
│   ├── preprocess.py           # Module 1: Imputation
│   ├── forecast.py             # Module 2: Forecasting
│   └── optimize.py             # Module 3: Optimization
└── utils/
    ├── styles.py               # CSS design system
    ├── session.py              # Session state management
    ├── charts.py               # Plotly chart library
    ├── imputation.py           # Imputation logic
    ├── forecasting.py          # Forecasting engine
    └── opt_input_builder.py    # Optimization input builder
```

## Design System

The dashboard replicates the navy/teal/amber dark theme from the HTML reference:

- **Colors:** Navy `#0d1b2a`, Teal `#1bb8a0`, Amber `#f5a623`, Rose `#e05c7a`
- **Fonts:** Fraunces (headings), DM Sans (body), DM Mono (numbers/code)
- **Charts:** Plotly with custom dark theme matching the design tokens
