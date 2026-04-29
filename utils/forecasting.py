"""
Demand forecasting engine.
Exact port of rf_sarima_tsb_adjusted.py — models: RandomForest_2Stage, SARIMA, TSB.
MovingAverage_3 / SeasonalNaive / LastValue exist only as fallbacks inside
choose_best_model_for_fold, exactly as in the original file.
Summary columns match the original: Average_Validation_MAE, Average_Validation_MAPE.
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import mean_absolute_error

try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    _SARIMA_AVAILABLE = True
except ImportError:
    _SARIMA_AVAILABLE = False

# ── Settings (match original file exactly) ─────────────────────────────────
RANDOM_STATE          = 42
VALIDATION_WINDOW_MONTHS = 3
RF_N_ESTIMATORS       = 500
RF_MAX_DEPTH          = 14
RF_MIN_LEAF           = 2
RF_MIN_SAMPLES_SPLIT  = 4
TSB_ALPHA_GRID        = [0.05, 0.10, 0.20, 0.30]
TSB_BETA_GRID         = [0.05, 0.10, 0.20, 0.30]
SARIMA_MIN_HISTORY    = 18
SARIMA_MIN_NONZERO    = 8
SARIMA_MAX_ZERO_RATIO = 0.40
SARIMA_MAXITER        = 200


# ── Preprocessing ───────────────────────────────────────────────────────────
def preprocess_data(df):
    df = df.copy()
    for col in ["Year","Month","Monthly_QTY","Imputed_Demand",
                "Opening_Inventory_Qty","Ending_Inventory_Qty"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["SKU","Year","Month"])
    df["Year"]  = df["Year"].astype(int)
    df["Month"] = df["Month"].astype(int)
    df["Date"]  = pd.to_datetime(
        dict(year=df["Year"], month=df["Month"], day=1), errors="coerce")
    return df.dropna(subset=["Date"]).sort_values(["SKU","Date"]).reset_index(drop=True)


def get_model_demand_series(window_df):
    return window_df.set_index("Date")["Imputed_Demand"].astype(float).asfreq("MS")


# ── Metrics ─────────────────────────────────────────────────────────────────
def safe_mape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom  = np.where(np.abs(y_true) < 1e-8, 1.0, np.abs(y_true))
    return float(np.mean(np.abs((y_true - y_pred) / denom)) * 100)


def evaluate_predictions(y_true, y_pred):
    mae  = mean_absolute_error(y_true, y_pred)
    mape = safe_mape(y_true, y_pred)
    rmse = float(np.sqrt(np.mean((np.asarray(y_true) - np.asarray(y_pred))**2)))
    return float(mae), float(mape), rmse


def get_prediction_cap(train_series):
    values = np.asarray(train_series, dtype=float)
    if len(values) == 0: return 0.0
    p95 = float(np.percentile(values,95)) if len(values)>=5 else float(np.max(values))
    return float(max(
        max(1.0, float(np.max(values))*2.25),
        max(1.0, float(np.mean(values))+2.0*float(np.std(values))),
        max(1.0, p95*1.75),
    ))


def clip_predictions(preds, train_series):
    cap   = get_prediction_cap(train_series)
    preds = np.clip(np.asarray(preds, dtype=float), 0.0, cap)
    return preds.tolist(), cap


def classify_demand(train_series):
    arr = np.asarray(train_series, dtype=float)
    if len(arr) == 0: return "insufficient"
    zero_ratio    = float(np.mean(arr == 0))
    nonzero_count = int(np.sum(arr > 0))
    coeff_var     = float(np.std(arr)/np.mean(arr[arr>0])) if np.any(arr>0) else np.inf
    if len(arr)<8 or nonzero_count<4: return "insufficient"
    if zero_ratio >= 0.50:            return "intermittent"
    if coeff_var > 1.0:               return "erratic"
    return "smooth"


def months_since_last_nonzero(history):
    for i,v in enumerate(reversed(history), start=1):
        if v > 0: return i-1
    return len(history)


def trailing_zero_run(history):
    count = 0
    for v in reversed(history):
        if v == 0: count += 1
        else: break
    return count


def moving_average(values, k):
    return float(np.mean(list(values)[-k:])) if values else 0.0


def month_of_year_stats(history_values, history_dates, target_month):
    month_vals = [float(v) for d,v in zip(history_dates, history_values)
                  if int(pd.Timestamp(d).month)==int(target_month)]
    if not month_vals: return 0.0, 0.0, 0.0
    pos = [v for v in month_vals if v>0]
    return float(np.mean(month_vals)), float(np.median(month_vals)), float(np.mean(pos)) if pos else 0.0


# ── RF Features ─────────────────────────────────────────────────────────────
def create_time_features(history_values, history_dates, current_date, step_number):
    history       = [float(v) for v in history_values]
    history_dates = list(pd.DatetimeIndex(history_dates))

    def lag(k):            return history[-k] if len(history)>=k else 0.0
    def rolling_std(k):    return float(np.std(history[-k:]))    if len(history)>1  else 0.0
    def rolling_median(k): return float(np.median(history[-k:])) if history         else 0.0
    def nonzero_ratio(k):  return float(np.mean(np.array(history[-k:])>0)) if history else 0.0

    recent_nz   = [v for v in reversed(history) if v>0]
    last_nz     = float(recent_nz[0]) if recent_nz else 0.0
    l1,l2,l3,l6,l12 = lag(1),lag(2),lag(3),lag(6),lag(12)
    month       = int(current_date.month)
    year        = int(current_date.year)
    mm,md,mp    = month_of_year_stats(history, history_dates, month)
    r3  = history[-3:]  if len(history)>=3  else history
    r6  = history[-6:]  if len(history)>=6  else history
    r12 = history[-12:] if len(history)>=12 else history
    m3  = float(np.mean(r3))  if r3  else 0.0
    m6  = float(np.mean(r6))  if r6  else 0.0
    m12 = float(np.mean(r12)) if r12 else 0.0

    return {
        "Year":year,"Month":month,
        "Month_Sin":np.sin(2*np.pi*month/12),"Month_Cos":np.cos(2*np.pi*month/12),
        "Lag_1":l1,"Lag_2":l2,"Lag_3":l3,"Lag_6":l6,"Lag_12":l12,
        "Lag_Diff_1_2":l1-l2,"Lag_Diff_1_3":l1-l3,"Lag_Diff_3_6":l3-l6,
        "Rolling_Mean_3":m3,"Rolling_Mean_6":m6,"Rolling_Mean_12":m12,
        "Rolling_Median_3":rolling_median(3),"Rolling_Median_6":rolling_median(6),
        "Rolling_Std_3":rolling_std(3),"Rolling_Std_6":rolling_std(6),"Rolling_Std_12":rolling_std(12),
        "Nonzero_Ratio_3":nonzero_ratio(3),"Nonzero_Ratio_6":nonzero_ratio(6),"Nonzero_Ratio_12":nonzero_ratio(12),
        "Last_Nonzero":last_nz,
        "Months_Since_Last_Nonzero":months_since_last_nonzero(history),
        "Trailing_Zero_Run":trailing_zero_run(history),
        "Month_Mean_History":mm,"Month_Median_History":md,"Month_Positive_Mean_History":mp,
        "Trend_3_over_6":m3-m6,"Trend_6_over_12":m6-m12,
        "Global_Mean":float(np.mean(history)) if history else 0.0,
        "Global_Std":float(np.std(history))   if len(history)>1 else 0.0,
        "Step_Number":int(step_number),
    }


FEATURE_COLS = [
    "Year","Month","Month_Sin","Month_Cos","Lag_1","Lag_2","Lag_3",
    "Lag_6","Lag_12","Lag_Diff_1_2","Lag_Diff_1_3","Lag_Diff_3_6",
    "Rolling_Mean_3","Rolling_Mean_6","Rolling_Mean_12","Rolling_Median_3",
    "Rolling_Median_6","Rolling_Std_3","Rolling_Std_6","Rolling_Std_12",
    "Nonzero_Ratio_3","Nonzero_Ratio_6","Nonzero_Ratio_12","Last_Nonzero",
    "Months_Since_Last_Nonzero","Trailing_Zero_Run","Month_Mean_History",
    "Month_Median_History","Month_Positive_Mean_History","Trend_3_over_6",
    "Trend_6_over_12","Global_Mean","Global_Std","Step_Number",
]


def build_rf_training_data(series):
    rows   = []
    values = series.values.astype(float)
    dates  = series.index
    for i in range(3, len(series)):
        row = create_time_features(values[:i], dates[:i], dates[i], i+1)
        row["Target"]             = float(values[i])
        row["Target_Is_Positive"] = int(float(values[i])>0)
        rows.append(row)
    return pd.DataFrame(rows)


# ── Baselines + TSB (exact copy from original) ──────────────────────────────
def fit_predict_last_value(train_series, forecast_steps):
    last_val = float(train_series.iloc[-1]) if len(train_series)>0 else 0.0
    p, cap   = clip_predictions([last_val]*forecast_steps, train_series)
    return p, {"cap":cap,"status":"ok"}


def fit_predict_moving_average(train_series, forecast_steps, window=3):
    avg    = moving_average(train_series.astype(float).tolist(), window)
    p, cap = clip_predictions([avg]*forecast_steps, train_series)
    return p, {"cap":cap,"status":"ok","window":window}


def fit_predict_seasonal_naive(train_series, forecast_dates):
    values = train_series.astype(float)
    preds  = []
    for dt in forecast_dates:
        prior = dt - pd.DateOffset(years=1)
        preds.append(float(values.loc[prior]) if prior in values.index
                     else float(values.iloc[-1]) if len(values)>0 else 0.0)
    p, cap = clip_predictions(preds, train_series)
    return p, {"cap":cap,"status":"ok"}


def tsb_forecast_with_params(train_series, forecast_steps, alpha, beta):
    y = np.asarray(train_series, dtype=float)
    if len(y)==0: return [0.0]*forecast_steps
    z = max(0.0, next((float(v) for v in y if v>0), 0.0))
    p = min(1.0, max(0.0, float(np.mean(y>0))))
    for actual in y:
        p = beta*(1.0 if actual>0 else 0.0)+(1.0-beta)*p
        if actual>0: z = alpha*actual+(1.0-alpha)*z
    return [max(0.0, z*p)]*forecast_steps


def fit_predict_tsb(train_series, validation_series_or_steps):
    if isinstance(validation_series_or_steps, int):
        preds  = tsb_forecast_with_params(train_series, validation_series_or_steps, 0.10, 0.10)
        p, cap = clip_predictions(preds, train_series)
        return p, {"cap":cap,"status":"ok","alpha":0.10,"beta":0.10}
    y_val       = np.asarray(validation_series_or_steps, dtype=float)
    best_score  = np.inf
    best_preds  = None
    best_params = (0.10, 0.10)
    for alpha in TSB_ALPHA_GRID:
        for beta in TSB_BETA_GRID:
            hist  = list(np.asarray(train_series, dtype=float))
            preds = []
            for actual in y_val:
                pred = tsb_forecast_with_params(hist, 1, alpha, beta)[0]
                preds.append(pred)
                hist.append(float(actual))
            mae,_,rmse = evaluate_predictions(y_val, preds)
            score = mae+0.1*rmse
            if score < best_score:
                best_score, best_preds, best_params = score, preds, (alpha, beta)
    p, cap = clip_predictions(best_preds, train_series)
    return p, {"cap":cap,"status":"ok","alpha":best_params[0],"beta":best_params[1]}


# ── Random Forest (exact copy from original) ────────────────────────────────
def fit_predict_random_forest_v2(train_series, forecast_dates):
    train_df      = build_rf_training_data(train_series)
    history       = list(train_series.values.astype(float))
    history_dates = list(train_series.index)
    if train_df.empty:
        p, cap = clip_predictions([0.0]*len(forecast_dates), train_series)
        return p, {"cap":cap,"status":"fallback_zero"}

    X_all = train_df[FEATURE_COLS]
    y_occ = train_df["Target_Is_Positive"]

    if y_occ.nunique()==1:
        always_positive = int(y_occ.iloc[0])==1
        occ_model       = None
    else:
        always_positive = False
        occ_model = RandomForestClassifier(
            n_estimators=RF_N_ESTIMATORS, max_depth=RF_MAX_DEPTH,
            min_samples_leaf=RF_MIN_LEAF, min_samples_split=RF_MIN_SAMPLES_SPLIT,
            random_state=RANDOM_STATE, n_jobs=-1, class_weight="balanced_subsample",
        ).fit(X_all, y_occ)

    pos_df     = train_df[train_df["Target_Is_Positive"]==1].copy()
    size_model = None
    if len(pos_df)>=5:
        size_model = RandomForestRegressor(
            n_estimators=RF_N_ESTIMATORS, max_depth=RF_MAX_DEPTH,
            min_samples_leaf=RF_MIN_LEAF, min_samples_split=RF_MIN_SAMPLES_SPLIT,
            random_state=RANDOM_STATE, n_jobs=-1,
        ).fit(pos_df[FEATURE_COLS], pos_df["Target"])

    hist_nzr   = float(np.mean(np.asarray(history)>0)) if history else 0.0
    hist_mean_pos = float(np.mean([x for x in history if x>0])) if any(x>0 for x in history) else 0.0
    demand_type   = classify_demand(pd.Series(history))

    preds = []
    pos_count = 0
    for step_number, future_date in enumerate(forecast_dates, start=1):
        feat     = create_time_features(history, history_dates, future_date, len(history)+1)
        X_future = pd.DataFrame([feat])[FEATURE_COLS]

        if occ_model is None:
            prob_pos = 1.0 if always_positive else 0.0
        else:
            proba   = occ_model.predict_proba(X_future)
            pos_idx = int(np.where(occ_model.classes_==1)[0][0])
            prob_pos = float(proba[0, pos_idx])

        thresh = 0.50
        if hist_nzr < 0.35:                               thresh = 0.58
        if trailing_zero_run(history) >= 3:               thresh += 0.05
        if demand_type == "intermittent":                  thresh = max(thresh, 0.60)
        max_pos_rate = min(0.95, hist_nzr+0.20)
        if (pos_count+1)/max(1,step_number) > max_pos_rate: thresh = max(thresh, 0.70)

        mm  = float(feat["Month_Mean_History"])
        mp  = float(feat["Month_Positive_Mean_History"])
        rm  = float(feat["Rolling_Mean_3"])
        rmd = float(feat["Rolling_Median_3"])

        if prob_pos < thresh:
            pred = 0.0
        else:
            rf_sz = (max(hist_mean_pos, mp, mm) if size_model is None
                     else float(size_model.predict(X_future)[0]))
            pred  = 0.45*rf_sz + 0.20*mm + 0.15*mp + 0.10*rm + 0.10*rmd
            pred *= max(0.60, prob_pos)
            pred += 0.25*float(feat["Trend_3_over_6"])
            if mm>0: pred = 0.75*pred + 0.25*mm
            pred = max(0.0, pred)
            if pred>0: pos_count += 1

        preds.append(pred)
        history.append(pred)
        history_dates.append(pd.Timestamp(future_date))

    p, cap = clip_predictions(preds, train_series)
    return p, {"cap":cap,"status":"ok"}


# ── SARIMA (exact copy from original) ───────────────────────────────────────
def sarima_eligible(train_series):
    if not _SARIMA_AVAILABLE: return False, "statsmodels not available"
    values = np.asarray(train_series, dtype=float)
    nz     = int(np.sum(values>0))
    zr     = float(np.mean(values==0)) if len(values)>0 else 1.0
    if len(values) < SARIMA_MIN_HISTORY:    return False, f"Skipped SARIMA: history<{SARIMA_MIN_HISTORY}"
    if nz           < SARIMA_MIN_NONZERO:   return False, f"Skipped SARIMA: nonzero_count<{SARIMA_MIN_NONZERO}"
    if zr           > SARIMA_MAX_ZERO_RATIO:return False, f"Skipped SARIMA: zero_ratio>{SARIMA_MAX_ZERO_RATIO:.2f}"
    return True, "eligible"


def fit_predict_sarima_v2(train_series, forecast_steps):
    ok, note = sarima_eligible(train_series)
    if not ok: raise ValueError(note)
    values = train_series.astype(float).copy()
    values.index = pd.DatetimeIndex(values.index)
    values = values.asfreq("MS")
    candidates = [
        ((1,0,0),(0,0,0,0),"c"),((0,0,1),(0,0,0,0),"c"),((1,0,1),(0,0,0,0),"c"),
        ((1,1,0),(0,0,0,0),"n"),((0,1,1),(0,0,0,0),"n"),((1,1,1),(0,0,0,0),"n"),
    ]
    if len(values)>=24:
        candidates+=[ ((1,0,0),(0,1,1,12),"n"),((0,1,1),(0,1,1,12),"n") ]
    best_aic, best_result = np.inf, None
    for order,seasonal_order,trend in candidates:
        try:
            res = SARIMAX(values, order=order, seasonal_order=seasonal_order,
                          trend=trend, simple_differencing=False,
                          enforce_stationarity=False, enforce_invertibility=False
                         ).fit(disp=False, maxiter=SARIMA_MAXITER)
            mle_ok = True
            if hasattr(res,"mle_retvals") and isinstance(res.mle_retvals,dict):
                mle_ok = bool(res.mle_retvals.get("converged",True))
            if not mle_ok: continue
            if np.isfinite(res.aic) and res.aic < best_aic:
                best_aic, best_result = res.aic, res
        except Exception: continue
    if best_result is None: raise ValueError("All SARIMA fits failed or did not converge.")
    preds = np.asarray(best_result.forecast(steps=forecast_steps), dtype=float)
    raw_cap     = get_prediction_cap(values)
    max_allowed = max(raw_cap, float(np.max(values))*2.25)
    if np.any(~np.isfinite(preds)):              raise ValueError("SARIMA produced non-finite forecasts.")
    if len(preds)>0 and float(np.max(preds))>max_allowed: raise ValueError("SARIMA forecast rejected: unstable/explosive.")
    if len(preds)>1 and float(np.std(preds))==0.0 and float(np.std(values[-6:]))>0.0:
        raise ValueError("SARIMA forecast rejected: completely flat.")
    p, cap = clip_predictions(preds, values)
    return p, {"cap":cap,"status":"ok"}


# ── Model selection per fold (exact copy from original) ─────────────────────
def choose_best_model_for_fold(train_series, validation_series):
    demand_type      = classify_demand(train_series)
    notes            = []
    model_scores     = []
    validation_dates = validation_series.index
    y_val            = validation_series.values.astype(float)

    if len(train_series)<5 or len(validation_series.dropna())==0:
        return {"Best_Model":"LastValue","Demand_Type":demand_type,
                "Best_Validation_MAE":np.nan,"Best_Validation_MAPE":np.nan,
                "Validation_Note":"Not enough history or validation months. Defaulted to LastValue."}

    candidates = [
        ("RandomForest_2Stage", lambda: fit_predict_random_forest_v2(train_series, validation_dates)),
        ("TSB",                 lambda: fit_predict_tsb(train_series, y_val)),
        ("SeasonalNaive",       lambda: fit_predict_seasonal_naive(train_series, validation_dates)),
        ("MovingAverage_3",     lambda: fit_predict_moving_average(train_series, len(validation_dates), 3)),
        ("LastValue",           lambda: fit_predict_last_value(train_series, len(validation_dates))),
    ]
    ok, sarima_note = sarima_eligible(train_series)
    if ok:   candidates.append(("SARIMA", lambda: fit_predict_sarima_v2(train_series, len(validation_dates))))
    else:    notes.append(sarima_note)

    for model_name, func in candidates:
        try:
            preds,_ = func()
            mae,mape,rmse = evaluate_predictions(y_val, preds)
            hist_nzr = float(np.mean(np.asarray(train_series)>0))
            pred_nzr = float(np.mean(np.asarray(preds)>0)) if preds else 0.0
            pred_std = float(np.std(preds)) if len(preds)>1 else 0.0
            val_std  = float(np.std(y_val)) if len(y_val)>1  else 0.0
            penalty  = 0.0
            if hist_nzr<0.35 and pred_nzr>hist_nzr+0.25: penalty+=5.0
            if pred_std==0.0 and val_std>0.0:             penalty+=3.0
            if demand_type=="intermittent" and model_name=="TSB": penalty-=1.0
            score = mae+0.15*rmse+penalty
            model_scores.append({"Model":model_name,"MAE":float(mae),"MAPE":float(mape),"RMSE":float(rmse),"Score":float(score)})
        except Exception as e:
            notes.append(f"{model_name} failed: {e}")

    if not model_scores:
        return {"Best_Model":"LastValue","Demand_Type":demand_type,
                "Best_Validation_MAE":np.nan,"Best_Validation_MAPE":np.nan,
                "Validation_Note":"All models failed. Defaulted to LastValue."}

    best_row  = sorted(model_scores, key=lambda x:(x["Score"],x["MAE"],x["RMSE"]))[0]
    note_text = " | ".join(notes) if notes else "Model chosen using rolling validation."
    return {"Best_Model":best_row["Model"],"Demand_Type":demand_type,
            "Best_Validation_MAE":best_row["MAE"],"Best_Validation_MAPE":best_row["MAPE"],
            "Validation_Note":note_text}


def forecast_with_model(train_series, model_name, forecast_dates):
    if model_name=="SARIMA":              return fit_predict_sarima_v2(train_series, len(forecast_dates))
    if model_name=="TSB":                 return fit_predict_tsb(train_series, len(forecast_dates))
    if model_name=="RandomForest_2Stage": return fit_predict_random_forest_v2(train_series, forecast_dates)
    if model_name=="SeasonalNaive":       return fit_predict_seasonal_naive(train_series, forecast_dates)
    if model_name=="MovingAverage_3":     return fit_predict_moving_average(train_series, len(forecast_dates), 3)
    return fit_predict_last_value(train_series, len(forecast_dates))


# ── Dynamic rolling folds ────────────────────────────────────────────────────
def generate_rolling_folds(last_date, forecast_months):
    """4 rolling folds relative to last_date, matching original fold structure."""
    folds = []
    for fold_num in range(1, 5):
        offset    = (4 - fold_num) * VALIDATION_WINDOW_MONTHS
        val_end   = (last_date - pd.DateOffset(months=offset)).replace(day=1)
        val_start = (val_end - pd.DateOffset(months=VALIDATION_WINDOW_MONTHS-1)).replace(day=1)
        fc_start  = (val_end + pd.DateOffset(months=1)).replace(day=1)
        fc_end    = (fc_start + pd.DateOffset(months=VALIDATION_WINDOW_MONTHS-1)).replace(day=1)
        folds.append({"fold":fold_num,"validation_start":val_start,"validation_end":val_end,
                       "forecast_start":fc_start,"forecast_end":fc_end})
    return folds


def forecast_future_for_sku(sku_df, forecast_months, last_date):
    sku_df    = sku_df.sort_values("Date").copy()
    all_folds = generate_rolling_folds(last_date, forecast_months)
    fold_summaries = []

    for fi in all_folds:
        fold_num  = fi["fold"]
        val_start = fi["validation_start"]
        val_end   = fi["validation_end"]
        fc_start  = fi["forecast_start"]
        fc_end    = fi["forecast_end"]

        train_window = sku_df[sku_df["Date"] < val_start].copy()
        val_window   = sku_df[(sku_df["Date"]>=val_start)&(sku_df["Date"]<=val_end)].copy()

        if train_window.empty or val_window.empty:
            fold_summaries.append({
                "Fold":fold_num,
                "Validation_Period":f"{val_start.strftime('%Y-%m')} to {val_end.strftime('%Y-%m')}",
                "Forecast_Period":  f"{fc_start.strftime('%Y-%m')} to {fc_end.strftime('%Y-%m')}",
                "Best_Model":"Skipped","Demand_Type":"insufficient",
                "Best_Validation_MAE":np.nan,"Best_Validation_MAPE":np.nan,
                "Validation_Note":"Missing train or validation rows.",
            })
            continue

        train_series = get_model_demand_series(train_window)
        val_series   = get_model_demand_series(val_window)
        model_info   = choose_best_model_for_fold(train_series, val_series)

        fold_summaries.append({
            "Fold":fold_num,
            "Validation_Period":f"{val_start.strftime('%Y-%m')} to {val_end.strftime('%Y-%m')}",
            "Forecast_Period":  f"{fc_start.strftime('%Y-%m')} to {fc_end.strftime('%Y-%m')}",
            "Best_Model":            model_info["Best_Model"],
            "Demand_Type":           model_info["Demand_Type"],
            "Best_Validation_MAE":   model_info["Best_Validation_MAE"],
            "Best_Validation_MAPE":  model_info["Best_Validation_MAPE"],
            "Validation_Note":       model_info["Validation_Note"],
        })

    usable = [f for f in fold_summaries if f["Best_Model"]!="Skipped"]
    if usable:
        from collections import Counter
        dominant_model = Counter([f["Best_Model"] for f in usable]).most_common(1)[0][0]
        dominant_type  = pd.Series([f["Demand_Type"] for f in usable]).mode()[0]
        avg_mae        = float(np.nanmean([f["Best_Validation_MAE"]  for f in usable]))
        avg_mape       = float(np.nanmean([f["Best_Validation_MAPE"] for f in usable]))
        notes          = " | ".join([f"Fold {f['Fold']}: {f['Best_Model']}" for f in usable])
    else:
        dominant_model,dominant_type = "LastValue","insufficient"
        avg_mae = avg_mape = np.nan
        notes   = "All folds skipped."

    full_series  = get_model_demand_series(sku_df)
    future_dates = pd.date_range(
        start=last_date + pd.DateOffset(months=1), periods=forecast_months, freq="MS")

    try:
        preds, _ = forecast_with_model(full_series, dominant_model, future_dates)
        fc_note  = "ok"
    except Exception as e:
        preds, _ = fit_predict_last_value(full_series, len(future_dates))
        fc_note  = f"Fallback LastValue: {e}"
        dominant_model = "LastValue (fallback)"

    prediction_rows = []
    for dt, pred in zip(future_dates, preds):
        prediction_rows.append({
            "Date":dt,"Year":int(dt.year),"Month":int(dt.month),
            "Demand_Prediction":round(float(pred),4),
            "Best_Model":dominant_model,"Demand_Type":dominant_type,
            "Best_Validation_MAE":avg_mae,"Best_Validation_MAPE":avg_mape,
            "Validation_Note":notes+(f" | {fc_note}" if fc_note!="ok" else ""),
        })
    return prediction_rows, fold_summaries, dominant_model, dominant_type, avg_mae, avg_mape, notes


# ── Top-level pipeline — output columns match original run_pipeline exactly ──
def run_forecast_pipeline(imputed_df, selected_skus, adi_threshold,
                          cv2_threshold, forecast_months, progress_cb=None):
    """
    Returns (detail_df, summary_df, fold_df).
    summary_df columns: SKU, Best_Model_Used, Demand_Type, Forecast_Months_2025,
                        Average_Validation_MAE, Average_Validation_MAPE, Notes
    """
    from utils.imputation import compute_sku_stats, apply_thresholds

    df = imputed_df.copy()
    df = df[df["SKU"].isin(selected_skus)].copy()
    df = preprocess_data(df)

    stats         = compute_sku_stats(df)
    stats         = apply_thresholds(stats, adi_threshold, cv2_threshold)
    eligible_skus = stats[stats["pass_filter"]]["SKU"].tolist()

    last_date = df["Date"].max()

    # Initialise output columns (match original run_pipeline)
    df["Original_Monthly_QTY"]  = df["Monthly_QTY"]
    df["Demand_Used_For_Model"]  = df["Imputed_Demand"]
    for col in ["Best_Model","Demand_Type","Validation_Note"]:
        df[col] = pd.Series([None]*len(df), dtype="object")
    for col in ["Best_Validation_MAE","Best_Validation_MAPE","Fold_Number","Demand_Prediction"]:
        df[col] = np.nan

    summary_rows = []
    fold_rows    = []
    total        = len(eligible_skus)

    for i, sku in enumerate(eligible_skus):
        if progress_cb:
            progress_cb(i, total, sku)

        sku_df = df[df["SKU"]==sku].copy().sort_values("Date")

        try:
            pred_rows, fold_sums, dom_model, dom_type, avg_mae, avg_mape, notes = \
                forecast_future_for_sku(sku_df, forecast_months, last_date)
        except Exception as e:
            pred_rows, fold_sums = [], []
            dom_model, dom_type  = "Error", "insufficient"
            avg_mae = avg_mape   = np.nan
            notes                = f"Pipeline error: {e}"

        for fs in fold_sums:
            fold_rows.append({"SKU":sku, **fs})

        future_rows = []
        for pr in pred_rows:
            future_rows.append({
                "SKU":sku,"Year":pr["Year"],"Month":pr["Month"],"Date":pr["Date"],
                "Monthly_QTY":np.nan,"Imputed_Demand":np.nan,
                "Opening_Inventory_Qty":np.nan,"Ending_Inventory_Qty":np.nan,
                "Original_Monthly_QTY":np.nan,"Demand_Used_For_Model":np.nan,
                "Best_Model":pr["Best_Model"],"Demand_Type":pr["Demand_Type"],
                "Best_Validation_MAE":pr["Best_Validation_MAE"],
                "Best_Validation_MAPE":pr["Best_Validation_MAPE"],
                "Validation_Note":pr["Validation_Note"],
                "Fold_Number":np.nan,"Demand_Prediction":pr["Demand_Prediction"],
            })

        if future_rows:
            df = pd.concat([df, pd.DataFrame(future_rows)], ignore_index=True)

        # ── Summary row — column names EXACTLY match original run_pipeline ──
        summary_rows.append({
            "SKU":                     sku,
            "Best_Model_Used":         dom_model,
            "Demand_Type":             dom_type,
            "Forecast_Months_2025":    len(pred_rows),
            "Average_Validation_MAE":  avg_mae,    # ← exact original name
            "Average_Validation_MAPE": avg_mape,   # ← exact original name
            "Notes":                   notes,
        })

    summary_df = pd.DataFrame(summary_rows).sort_values("SKU").reset_index(drop=True)
    fold_df    = (pd.DataFrame(fold_rows).sort_values(["SKU","Fold"]).reset_index(drop=True)
                  if fold_rows else pd.DataFrame())

    return df, summary_df, fold_df
