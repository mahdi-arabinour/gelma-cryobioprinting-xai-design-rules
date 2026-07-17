# Reproducible pipeline for explainable design-rule discovery in GelMA-HUVEC cryobioprinting data

import os
import json
import zipfile
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib

from sklearn.model_selection import GroupKFold
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.dummy import DummyRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

warnings.filterwarnings("ignore", category=FutureWarning)

SEED = 42
np.random.seed(SEED)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_VERSION = "1.0.0"
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
TABLE_DIR = OUTPUT_DIR / "tables"
FIGURE_DIR = OUTPUT_DIR / "figures"
MODEL_DIR = OUTPUT_DIR / "models"

for d in [OUTPUT_DIR, TABLE_DIR, FIGURE_DIR, MODEL_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DATA_PATH = DATA_DIR / "processed" / "qiao_2023_gelma_huvec_viability_100_formulations.csv"

def save_table(df, name):
    path_csv = TABLE_DIR / f"{name}.csv"
    path_xlsx = TABLE_DIR / f"{name}.xlsx"
    df.to_csv(path_csv, index=False)
    try:
        df.to_excel(path_xlsx, index=False)
    except Exception:
        pass
    return path_csv

def save_figure(name):
    path_png = FIGURE_DIR / f"{name}.png"
    path_pdf = FIGURE_DIR / f"{name}.pdf"
    try:
        plt.tight_layout()
    except Exception:
        pass
    plt.savefig(path_png, dpi=300, bbox_inches="tight")
    plt.savefig(path_pdf, bbox_inches="tight")
    plt.close()

def standardize_original_s2_format(df):
    df = df.copy()
    required_standard = {
        "formulation_id", "permeable_cpa", "permeable_conc",
        "sugar_cpa", "sugar_conc", "Day1", "Day7", "Day15"
    }
    
    if required_standard.issubset(set(df.columns)):
        return df
    
    original_cols = {"EG", "EGP", "GL", "GLP", "RA", "RAP", "LA", "LAP", "TR", "TRP", "Day1", "Day7", "Day15"}
    
    if not original_cols.issubset(set(df.columns)):
        raise ValueError(
            "Input data must contain either standardized columns or original S2-style columns."
        )
    
    rows = []
    
    for idx, row in df.iterrows():
        if row["EG"] == 1 or row["EGP"] > 0:
            permeable_cpa = "EG"
            permeable_conc = row["EGP"]
        elif row["GL"] == 1 or row["GLP"] > 0:
            permeable_cpa = "GL"
            permeable_conc = row["GLP"]
        else:
            permeable_cpa = "Not reported"
            permeable_conc = np.nan
        
        sugar_cpa = "None"
        sugar_conc = 0
        
        if row["RA"] == 1 or row["RAP"] > 0:
            sugar_cpa = "RA"
            sugar_conc = row["RAP"]
        elif row["LA"] == 1 or row["LAP"] > 0:
            sugar_cpa = "LA"
            sugar_conc = row["LAP"]
        elif row["TR"] == 1 or row["TRP"] > 0:
            sugar_cpa = "TR"
            sugar_conc = row["TRP"]
        
        formulation_id = f"{permeable_cpa}_{int(permeable_conc)}_{sugar_cpa}_{int(sugar_conc)}"
        
        out = row.to_dict()
        out.update({
            "formulation_id": formulation_id,
            "permeable_cpa": permeable_cpa,
            "permeable_conc": permeable_conc,
            "sugar_cpa": sugar_cpa,
            "sugar_conc": sugar_conc
        })
        
        rows.append(out)
    
    return pd.DataFrame(rows)

def load_data():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found: {DATA_PATH}. Place cleaned_S2_main_100_formulations.csv in the data folder."
        )
    
    # keep_default_na=False prevents categorical labels such as "None" from
    # being silently converted to missing values by pandas. The public
    # processed table uses the unambiguous label "NoSugar".
    df = pd.read_csv(DATA_PATH, keep_default_na=False)

    public_to_internal = {
        "permeable_conc_pct": "permeable_conc",
        "sugar_conc_pct": "sugar_conc",
        "viability_day1_pct": "Day1",
        "viability_day7_pct": "Day7",
        "viability_day15_pct": "Day15",
    }
    df = df.rename(columns={k: v for k, v in public_to_internal.items() if k in df.columns})
    df = standardize_original_s2_format(df)

    required = [
        "formulation_id", "permeable_cpa", "permeable_conc",
        "sugar_cpa", "sugar_conc", "Day1", "Day7", "Day15"
    ]
    missing_columns = [col for col in required if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    df["sugar_cpa"] = df["sugar_cpa"].replace({"NoSugar": "None"})

    for col in ["permeable_conc", "sugar_conc", "Day1", "Day7", "Day15"]:
        df[col] = pd.to_numeric(df[col], errors="raise")

    if df[required].isna().any().any():
        raise ValueError("The standardized dataset contains missing required values.")
    if df["formulation_id"].duplicated().any():
        raise ValueError("Duplicate formulation_id values were found.")
    if not df["permeable_cpa"].isin(["EG", "GL"]).all():
        raise ValueError("Unexpected permeable CPA category.")
    if not df["sugar_cpa"].isin(["None", "RA", "LA", "TR"]).all():
        raise ValueError("Unexpected sugar CPA category.")
    if not df["permeable_conc"].isin([5, 10, 15, 20]).all():
        raise ValueError("Unexpected permeable CPA concentration.")
    valid_sugar = (
        ((df["sugar_cpa"] == "None") & (df["sugar_conc"] == 0))
        | ((df["sugar_cpa"] != "None") & df["sugar_conc"].isin([5, 10, 15, 20]))
    )
    if not valid_sugar.all():
        raise ValueError("Sugar identity and concentration are inconsistent.")
    for col in ["Day1", "Day7", "Day15"]:
        if not df[col].between(0, 100).all():
            raise ValueError(f"{col} contains values outside 0-100%.")

    # Rebuild the internal identifier so output labels match the manuscript,
    # where no-sugar controls are denoted as "None".
    df["formulation_id"] = (
        df["permeable_cpa"].astype(str) + "_" +
        df["permeable_conc"].astype(int).astype(str) + "_" +
        df["sugar_cpa"].astype(str) + "_" +
        df["sugar_conc"].astype(int).astype(str)
    )

    if len(df) != 100 or df["formulation_id"].nunique() != 100:
        raise ValueError("Expected 100 unique formulations in the processed dataset.")

    return df

def design_space_check(df):
    expected = []
    
    for permeable in ["EG", "GL"]:
        for pconc in [5, 10, 15, 20]:
            expected.append({
                "permeable_cpa": permeable,
                "permeable_conc": pconc,
                "sugar_cpa": "None",
                "sugar_conc": 0,
                "formulation_id": f"{permeable}_{pconc}_None_0"
            })
            
            for sugar in ["RA", "LA", "TR"]:
                for sconc in [5, 10, 15, 20]:
                    expected.append({
                        "permeable_cpa": permeable,
                        "permeable_conc": pconc,
                        "sugar_cpa": sugar,
                        "sugar_conc": sconc,
                        "formulation_id": f"{permeable}_{pconc}_{sugar}_{sconc}"
                    })
    
    expected_df = pd.DataFrame(expected)
    observed_ids = set(df["formulation_id"])
    expected_ids = set(expected_df["formulation_id"])
    
    missing = expected_df[~expected_df["formulation_id"].isin(observed_ids)].copy()
    extra = df[~df["formulation_id"].isin(expected_ids)].copy()
    
    summary = pd.DataFrame([
        {"metric": "observed_formulations", "value": df["formulation_id"].nunique()},
        {"metric": "expected_full_factorial_formulations", "value": len(expected_df)},
        {"metric": "missing_expected_formulations", "value": len(missing)},
        {"metric": "extra_outside_expected_space", "value": len(extra)}
    ])
    
    save_table(summary, "Table_dataset_design_space_summary")
    save_table(missing, "Table_missing_expected_formulations")
    save_table(extra, "Table_extra_outside_expected_design_space")
    
    return summary, missing, extra

def engineer_features(df):
    df = df.copy()
    
    df["total_cpa_load"] = df["permeable_conc"] + df["sugar_conc"]
    df["has_sugar"] = (df["sugar_cpa"] != "None").astype(int)
    df["is_no_sugar_control"] = (df["sugar_cpa"] == "None").astype(int)
    df["is_ra_group"] = (df["sugar_cpa"] == "RA").astype(int)
    
    df["permeable_to_sugar_ratio"] = np.where(
        df["sugar_conc"] > 0,
        df["permeable_conc"] / df["sugar_conc"],
        np.nan
    )
    
    df["permeable_to_sugar_ratio_model"] = df["permeable_to_sugar_ratio"].fillna(0)
    
    df["retention_ratio"] = df["Day15"] / df["Day1"]
    df["early_loss"] = df["Day1"] - df["Day7"]
    df["late_response"] = df["Day15"] - df["Day7"]
    df["net_change"] = df["Day15"] - df["Day1"]
    df["time_decay_slope"] = (df["Day15"] - df["Day1"]) / 14.0
    
    trapezoid = getattr(np, "trapezoid", np.trapz)
    df["AUC"] = trapezoid(
        df[["Day1", "Day7", "Day15"]].values,
        x=np.array([1, 7, 15]),
        axis=1
    )
    df["AUC_normalized"] = df["AUC"] / (15 - 1)
    
    df["late_recovery_flag"] = (df["Day15"] > df["Day7"]).astype(int)
    df["late_recovery_magnitude"] = np.maximum(df["Day15"] - df["Day7"], 0)
    
    day15_z = (df["Day15"] - df["Day15"].mean()) / df["Day15"].std(ddof=1)
    net_abs_z = (df["net_change"].abs() - df["net_change"].abs().mean()) / df["net_change"].abs().std(ddof=1)
    df["stability_score"] = day15_z - net_abs_z
    
    return df

def make_long_format(df):
    long_rows = []
    
    for _, row in df.iterrows():
        for label, day in [("Day1", 1), ("Day7", 7), ("Day15", 15)]:
            item = row.to_dict()
            item["time_label"] = label
            item["storage_day"] = day
            item["cell_viability"] = row[label]
            item["total_cpa_load_x_time"] = row["total_cpa_load"] * day
            item["sugar_conc_x_time"] = row["sugar_conc"] * day
            item["permeable_conc_x_time"] = row["permeable_conc"] * day
            long_rows.append(item)
    
    return pd.DataFrame(long_rows)

def build_rf_pipeline(categorical_features, numeric_features, random_state=SEED):
    try:
        onehot = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        onehot = OneHotEncoder(handle_unknown="ignore", sparse=False)
    
    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", onehot, categorical_features),
            ("numeric", "passthrough", numeric_features)
        ],
        remainder="drop"
    )
    
    model = RandomForestRegressor(
        n_estimators=500,
        max_depth=None,
        min_samples_leaf=2,
        random_state=random_state,
        n_jobs=-1
    )
    
    return Pipeline([
        ("preprocessor", preprocessor),
        ("model", model)
    ])

def evaluate_grouped_model(df_long, feature_set_name, categorical_features, numeric_features):
    feature_cols = categorical_features + numeric_features
    
    X = df_long[feature_cols].copy()
    y = df_long["cell_viability"].copy()
    groups = df_long["formulation_id"].copy()
    
    gkf = GroupKFold(n_splits=5)
    rows = []
    pred_rows = []
    
    for fold_id, (train_idx, test_idx) in enumerate(gkf.split(X, y, groups), start=1):
        train_df = df_long.iloc[train_idx].copy()
        test_df = df_long.iloc[test_idx].copy()
        
        X_train = X.iloc[train_idx].copy()
        X_test = X.iloc[test_idx].copy()
        y_train = y.iloc[train_idx].copy()
        y_test = y.iloc[test_idx].copy()
        
        pipe = build_rf_pipeline(categorical_features, numeric_features, random_state=SEED + fold_id)
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)
        
        rows.append({
            "feature_set": feature_set_name,
            "fold": fold_id,
            "MAE": mean_absolute_error(y_test, y_pred),
            "RMSE": np.sqrt(mean_squared_error(y_test, y_pred)),
            "R2": r2_score(y_test, y_pred),
            "test_rows": len(test_idx),
            "test_formulations": test_df["formulation_id"].nunique()
        })
        
        pred_df = test_df[[
            "formulation_id", "permeable_cpa", "permeable_conc",
            "sugar_cpa", "sugar_conc", "time_label",
            "storage_day", "cell_viability"
        ]].copy()
        pred_df["feature_set"] = feature_set_name
        pred_df["fold"] = fold_id
        pred_df["predicted_viability"] = y_pred
        pred_df["absolute_error"] = np.abs(pred_df["cell_viability"] - pred_df["predicted_viability"])
        pred_rows.append(pred_df)
    
    return pd.DataFrame(rows), pd.concat(pred_rows, ignore_index=True)

def run_feature_ablation(df_long):
    feature_sets = {
        "basic_formulation_time": {
            "categorical": ["permeable_cpa", "sugar_cpa"],
            "numeric": ["permeable_conc", "sugar_conc", "storage_day"]
        },
        "basic_plus_load_ratio": {
            "categorical": ["permeable_cpa", "sugar_cpa"],
            "numeric": [
                "permeable_conc", "sugar_conc", "storage_day",
                "total_cpa_load", "permeable_to_sugar_ratio_model",
                "has_sugar", "is_no_sugar_control", "is_ra_group"
            ]
        },
        "time_interactions_only_added_to_basic": {
            "categorical": ["permeable_cpa", "sugar_cpa"],
            "numeric": [
                "permeable_conc", "sugar_conc", "storage_day",
                "total_cpa_load_x_time", "sugar_conc_x_time", "permeable_conc_x_time"
            ]
        },
        "full_with_time_interactions": {
            "categorical": ["permeable_cpa", "sugar_cpa"],
            "numeric": [
                "permeable_conc", "sugar_conc", "storage_day",
                "total_cpa_load", "permeable_to_sugar_ratio_model",
                "has_sugar", "is_no_sugar_control", "is_ra_group",
                "total_cpa_load_x_time", "sugar_conc_x_time", "permeable_conc_x_time"
            ]
        }
    }
    
    results = []
    predictions = []
    
    for name, spec in feature_sets.items():
        res, pred = evaluate_grouped_model(df_long, name, spec["categorical"], spec["numeric"])
        results.append(res)
        predictions.append(pred)
    
    results_df = pd.concat(results, ignore_index=True)
    predictions_df = pd.concat(predictions, ignore_index=True)
    
    summary = (
        results_df
        .groupby("feature_set")[["MAE", "RMSE", "R2"]]
        .agg(["mean", "std"])
        .reset_index()
    )
    
    save_table(results_df, "Ablation_fold_results")
    save_table(predictions_df, "Ablation_predictions")
    save_table(summary, "Ablation_summary")
    
    plt.figure(figsize=(8, 5))
    temp = results_df.groupby("feature_set")["MAE"].agg(["mean", "std"]).reset_index()
    temp = temp.sort_values("mean", ascending=True)
    plt.barh(temp["feature_set"], temp["mean"], xerr=temp["std"])
    plt.xlabel("MAE (%)")
    plt.ylabel("Feature set")
    plt.title("Feature-set ablation")
    save_figure("Figure_feature_set_ablation_MAE")
    
    return results_df, predictions_df, summary

def final_model_vs_baselines(df_long):
    categorical_features = ["permeable_cpa", "sugar_cpa"]
    numeric_features = ["permeable_conc", "sugar_conc", "storage_day"]
    feature_cols = categorical_features + numeric_features
    
    X = df_long[feature_cols].copy()
    y = df_long["cell_viability"].copy()
    groups = df_long["formulation_id"].copy()
    
    gkf = GroupKFold(n_splits=5)
    rows = []
    pred_rows = []
    
    for fold_id, (train_idx, test_idx) in enumerate(gkf.split(X, y, groups), start=1):
        train_df = df_long.iloc[train_idx].copy()
        test_df = df_long.iloc[test_idx].copy()
        
        X_train = X.iloc[train_idx].copy()
        X_test = X.iloc[test_idx].copy()
        y_train = y.iloc[train_idx].copy()
        y_test = y.iloc[test_idx].copy()
        
        global_model = DummyRegressor(strategy="mean")
        global_model.fit(X_train, y_train)
        y_pred_global = global_model.predict(X_test)
        
        time_means = train_df.groupby("time_label")["cell_viability"].mean().to_dict()
        y_pred_time = test_df["time_label"].map(time_means).fillna(train_df["cell_viability"].mean()).values
        
        final_rf = build_rf_pipeline(categorical_features, numeric_features, random_state=SEED + fold_id)
        final_rf.fit(X_train, y_train)
        y_pred_rf = final_rf.predict(X_test)
        
        model_predictions = {
            "GlobalMeanBaseline": y_pred_global,
            "TimeMeanBaseline": y_pred_time,
            "FinalBasicRandomForest": y_pred_rf
        }
        
        for model_name, y_pred in model_predictions.items():
            rows.append({
                "model": model_name,
                "fold": fold_id,
                "MAE": mean_absolute_error(y_test, y_pred),
                "RMSE": np.sqrt(mean_squared_error(y_test, y_pred)),
                "R2": r2_score(y_test, y_pred),
                "test_rows": len(test_idx),
                "test_formulations": test_df["formulation_id"].nunique()
            })
            
            pred_df = test_df[[
                "formulation_id", "permeable_cpa", "permeable_conc",
                "sugar_cpa", "sugar_conc", "time_label",
                "storage_day", "cell_viability"
            ]].copy()
            pred_df["model"] = model_name
            pred_df["fold"] = fold_id
            pred_df["predicted_viability"] = y_pred
            pred_df["absolute_error"] = np.abs(pred_df["cell_viability"] - pred_df["predicted_viability"])
            pred_rows.append(pred_df)
    
    perf_df = pd.DataFrame(rows)
    pred_df = pd.concat(pred_rows, ignore_index=True)
    
    summary = (
        perf_df
        .groupby("model")[["MAE", "RMSE", "R2"]]
        .agg(["mean", "std"])
        .reset_index()
    )
    
    save_table(perf_df, "Final_model_vs_baselines_fold_results")
    save_table(pred_df, "Final_model_vs_baselines_predictions")
    save_table(summary, "Final_model_vs_baselines_summary")
    
    plt.figure(figsize=(7, 5))
    temp = perf_df.groupby("model")["MAE"].mean().reset_index()
    plt.bar(temp["model"], temp["MAE"])
    plt.ylabel("MAE (%)")
    plt.xlabel("Model")
    plt.title("Final model vs baselines")
    plt.xticks(rotation=30, ha="right")
    save_figure("Figure_final_model_vs_baselines_MAE")
    
    rf_pred = pred_df[pred_df["model"] == "FinalBasicRandomForest"].copy()
    x = rf_pred["cell_viability"]
    yhat = rf_pred["predicted_viability"]
    low = min(x.min(), yhat.min())
    high = max(x.max(), yhat.max())
    
    plt.figure(figsize=(6, 6))
    plt.scatter(x, yhat, alpha=0.7)
    plt.plot([low, high], [low, high], linestyle="--")
    plt.xlabel("Observed viability (%)")
    plt.ylabel("Predicted viability (%)")
    plt.title("Observed vs predicted viability")
    save_figure("Figure_observed_vs_predicted")
    
    return perf_df, pred_df, summary

def bootstrap_ci(pred_df):
    rf_pred = pred_df[pred_df["model"] == "FinalBasicRandomForest"].copy()
    y_true = rf_pred["cell_viability"].values
    y_pred = rf_pred["predicted_viability"].values
    
    rng = np.random.default_rng(SEED)
    rows = []
    
    for _ in range(2000):
        idx = rng.choice(np.arange(len(y_true)), size=len(y_true), replace=True)
        rows.append({
            "MAE": mean_absolute_error(y_true[idx], y_pred[idx]),
            "RMSE": np.sqrt(mean_squared_error(y_true[idx], y_pred[idx])),
            "R2": r2_score(y_true[idx], y_pred[idx])
        })
    
    boot = pd.DataFrame(rows)
    ci = pd.DataFrame({
        "metric": ["MAE", "RMSE", "R2"],
        "mean": [boot["MAE"].mean(), boot["RMSE"].mean(), boot["R2"].mean()],
        "lower_95_CI": [boot["MAE"].quantile(0.025), boot["RMSE"].quantile(0.025), boot["R2"].quantile(0.025)],
        "upper_95_CI": [boot["MAE"].quantile(0.975), boot["RMSE"].quantile(0.975), boot["R2"].quantile(0.975)]
    })
    
    save_table(boot, "Final_model_bootstrap_distribution")
    save_table(ci, "Final_model_bootstrap_95CI")
    
    return boot, ci

def run_shap_analysis(df_long):
    import shap
    
    categorical_features = ["permeable_cpa", "sugar_cpa"]
    numeric_features = ["permeable_conc", "sugar_conc", "storage_day"]
    feature_cols = categorical_features + numeric_features
    
    X = df_long[feature_cols].copy()
    y = df_long["cell_viability"].copy()
    
    pipe = build_rf_pipeline(categorical_features, numeric_features, random_state=SEED)
    pipe.fit(X, y)

    joblib.dump(pipe, MODEL_DIR / "final_random_forest_pipeline.joblib")
    model_metadata = {
        "package_version": PACKAGE_VERSION,
        "model": "RandomForestRegressor",
        "n_estimators": 500,
        "max_depth": None,
        "min_samples_leaf": 2,
        "random_state": SEED,
        "categorical_features": categorical_features,
        "numeric_features": numeric_features,
        "target": "cell_viability",
        "validation": "5-fold GroupKFold grouped by formulation_id",
    }
    (MODEL_DIR / "model_metadata.json").write_text(
        json.dumps(model_metadata, indent=2), encoding="utf-8"
    )
    
    X_transformed = pipe.named_steps["preprocessor"].transform(X)
    cat_names = list(
        pipe.named_steps["preprocessor"]
        .named_transformers_["categorical"]
        .get_feature_names_out(categorical_features)
    )
    feature_names = cat_names + numeric_features
    X_transformed_df = pd.DataFrame(X_transformed, columns=feature_names)
    
    explainer = shap.TreeExplainer(pipe.named_steps["model"])
    shap_values = explainer.shap_values(X_transformed_df)
    
    if isinstance(shap_values, list):
        shap_values = shap_values[0]
    
    shap_importance = pd.DataFrame({
        "feature": feature_names,
        "mean_abs_SHAP": np.abs(shap_values).mean(axis=0)
    }).sort_values("mean_abs_SHAP", ascending=False)
    
    save_table(shap_importance, "Final_SHAP_global_importance")
    save_table(pd.DataFrame(shap_values, columns=feature_names), "Final_SHAP_values_matrix")
    
    plt.figure()
    shap.summary_plot(shap_values, X_transformed_df, max_display=20, show=False)
    save_figure("Figure_SHAP_beeswarm")
    
    plt.figure()
    shap.summary_plot(shap_values, X_transformed_df, plot_type="bar", max_display=20, show=False)
    save_figure("Figure_SHAP_bar")
    
    shap_df = pd.DataFrame(shap_values, columns=[f"SHAP_{c}" for c in feature_names])
    direction_df = pd.concat([
        df_long[[
            "formulation_id", "permeable_cpa", "permeable_conc",
            "sugar_cpa", "sugar_conc", "time_label",
            "storage_day", "cell_viability"
        ]].reset_index(drop=True),
        X_transformed_df.add_prefix("MODEL_").reset_index(drop=True),
        shap_df.reset_index(drop=True)
    ], axis=1)
    
    save_table(direction_df, "Final_SHAP_values_by_observation")
    
    continuous_rows = []
    
    for feature in ["permeable_conc", "sugar_conc", "storage_day"]:
        shap_col = f"SHAP_{feature}"
        temp = (
            direction_df
            .groupby(feature)
            .agg(
                mean_SHAP=(shap_col, "mean"),
                median_SHAP=(shap_col, "median"),
                mean_cell_viability=("cell_viability", "mean"),
                count=(feature, "count")
            )
            .reset_index()
        )
        temp["feature"] = feature
        continuous_rows.append(temp)
    
    continuous_direction = pd.concat(continuous_rows, ignore_index=True)
    save_table(continuous_direction, "Final_SHAP_direction_continuous_features")
    
    clean_rows = []
    
    for _, row in continuous_direction.iterrows():
        feature = row["feature"]
        level = row[feature]
        mean_shap = row["mean_SHAP"]
        
        if feature == "permeable_conc":
            level_label = f"{int(level)}% permeable CPA"
        elif feature == "sugar_conc":
            level_label = f"{int(level)}% sugar CPA"
        else:
            level_label = f"Day {int(level)}"
        
        if mean_shap > 1:
            direction = "Strong positive contribution"
        elif mean_shap > 0:
            direction = "Mild positive contribution"
        elif mean_shap < -1:
            direction = "Strong negative contribution"
        else:
            direction = "Mild negative contribution"
        
        clean_rows.append({
            "feature": feature,
            "level": level,
            "level_label": level_label,
            "mean_SHAP": mean_shap,
            "median_SHAP": row["median_SHAP"],
            "mean_cell_viability": row["mean_cell_viability"],
            "count": int(row["count"]),
            "directional_interpretation": direction
        })
    
    clean_direction = pd.DataFrame(clean_rows)
    save_table(clean_direction, "Final_SHAP_clean_directional_continuous_features")
    
    for feature in ["permeable_conc", "sugar_conc", "storage_day"]:
        temp = clean_direction[clean_direction["feature"] == feature].sort_values("level")
        plt.figure(figsize=(6, 4))
        plt.plot(temp["level"], temp["mean_SHAP"], marker="o")
        plt.axhline(0, linestyle="--")
        plt.xlabel(feature)
        plt.ylabel("Mean SHAP value")
        plt.title(f"Directional SHAP: {feature}")
        save_figure(f"Figure_directional_SHAP_{feature}")
    
    return pipe, shap_importance, direction_df, continuous_direction, clean_direction

def multiobjective_ranking(df_features):
    df = df_features.copy()
    
    rank_cols = {
        "Day15": "Day15_rank",
        "retention_ratio": "retention_rank",
        "AUC_normalized": "AUC_rank",
        "stability_score": "stability_rank"
    }
    
    for col, rank_col in rank_cols.items():
        df[rank_col] = df[col].rank(pct=True)
    
    df["multiobjective_score"] = (
        0.35 * df["Day15_rank"] +
        0.25 * df["retention_rank"] +
        0.20 * df["AUC_rank"] +
        0.20 * df["stability_rank"]
    )
    
    df["multiobjective_rank"] = df["multiobjective_score"].rank(ascending=False, method="first").astype(int)
    
    top_candidates = df.sort_values("multiobjective_score", ascending=False).copy()
    
    combo_summary = (
        df
        .groupby(["permeable_cpa", "sugar_cpa"])
        .agg(
            n=("formulation_id", "count"),
            mean_Day15=("Day15", "mean"),
            median_Day15=("Day15", "median"),
            mean_retention=("retention_ratio", "mean"),
            mean_AUC=("AUC_normalized", "mean"),
            mean_stability_score=("stability_score", "mean"),
            mean_multiobjective_score=("multiobjective_score", "mean"),
            late_recovery_rate=("late_recovery_flag", lambda x: 100 * np.mean(x))
        )
        .reset_index()
        .sort_values("mean_multiobjective_score", ascending=False)
    )
    
    conc_summary = (
        df
        .groupby(["permeable_conc", "sugar_conc"])
        .agg(
            n=("formulation_id", "count"),
            mean_Day15=("Day15", "mean"),
            mean_retention=("retention_ratio", "mean"),
            mean_AUC=("AUC_normalized", "mean"),
            mean_stability_score=("stability_score", "mean"),
            mean_multiobjective_score=("multiobjective_score", "mean")
        )
        .reset_index()
        .sort_values("mean_multiobjective_score", ascending=False)
    )
    
    save_table(top_candidates, "Multiobjective_all_candidate_ranking")
    save_table(top_candidates.head(20), "Multiobjective_top_20_candidate_formulations")
    save_table(combo_summary, "CPA_combination_design_rule_summary")
    save_table(conc_summary, "Concentration_design_rule_summary")
    
    plt.figure(figsize=(8, 6))
    temp = top_candidates.head(15).sort_values("multiobjective_score", ascending=True)
    plt.barh(temp["formulation_id"], temp["multiobjective_score"])
    plt.xlabel("Multi-objective score")
    plt.ylabel("Formulation")
    plt.title("Top candidate formulations")
    save_figure("Figure_top_candidate_formulations")
    
    return top_candidates, combo_summary, conc_summary

def sensitivity_analysis(df_ranked):
    schemes = {
        "balanced": {"Day15_rank": 0.35, "retention_rank": 0.25, "AUC_rank": 0.20, "stability_rank": 0.20},
        "equal_weights": {"Day15_rank": 0.25, "retention_rank": 0.25, "AUC_rank": 0.25, "stability_rank": 0.25},
        "Day15_priority": {"Day15_rank": 0.55, "retention_rank": 0.15, "AUC_rank": 0.15, "stability_rank": 0.15},
        "retention_priority": {"Day15_rank": 0.15, "retention_rank": 0.55, "AUC_rank": 0.15, "stability_rank": 0.15},
        "AUC_priority": {"Day15_rank": 0.15, "retention_rank": 0.15, "AUC_rank": 0.55, "stability_rank": 0.15},
        "stability_priority": {"Day15_rank": 0.15, "retention_rank": 0.15, "AUC_rank": 0.15, "stability_rank": 0.55}
    }
    
    all_rows = []
    
    for scheme_name, weights in schemes.items():
        temp = df_ranked.copy()
        score = np.zeros(len(temp))
        
        for col, w in weights.items():
            score += w * temp[col]
        
        temp["scheme"] = scheme_name
        temp["scheme_score"] = score
        temp["scheme_rank"] = temp["scheme_score"].rank(ascending=False, method="first").astype(int)
        all_rows.append(temp)
    
    sensitivity_df = pd.concat(all_rows, ignore_index=True)
    
    frequency = (
        sensitivity_df
        .groupby("formulation_id")
        .agg(
            top10_frequency=("scheme_rank", lambda x: np.sum(x <= 10)),
            top20_frequency=("scheme_rank", lambda x: np.sum(x <= 20)),
            mean_rank=("scheme_rank", "mean"),
            best_rank=("scheme_rank", "min"),
            worst_rank=("scheme_rank", "max")
        )
        .reset_index()
        .sort_values(["top10_frequency", "top20_frequency", "mean_rank"], ascending=[False, False, True])
    )
    
    save_table(sensitivity_df, "Sensitivity_all_scheme_rankings")
    save_table(frequency, "Sensitivity_candidate_frequency")
    
    plt.figure(figsize=(8, 6))
    temp = frequency.head(15).sort_values("top10_frequency", ascending=True)
    plt.barh(temp["formulation_id"], temp["top10_frequency"])
    plt.xlabel("Top-10 frequency across scoring schemes")
    plt.ylabel("Formulation")
    plt.title("Candidate robustness across sensitivity schemes")
    save_figure("Figure_sensitivity_candidate_frequency")
    
    return sensitivity_df, frequency

def generalization_tests(df_long):
    categorical_features = ["permeable_cpa", "sugar_cpa"]
    numeric_features = ["permeable_conc", "sugar_conc", "storage_day"]
    feature_cols = categorical_features + numeric_features
    
    def evaluate(train_df, test_df, name):
        pipe = build_rf_pipeline(categorical_features, numeric_features, random_state=SEED)
        pipe.fit(train_df[feature_cols], train_df["cell_viability"])
        y_pred = pipe.predict(test_df[feature_cols])
        y_true = test_df["cell_viability"]
        
        result = {
            "test_name": name,
            "train_rows": len(train_df),
            "test_rows": len(test_df),
            "train_formulations": train_df["formulation_id"].nunique(),
            "test_formulations": test_df["formulation_id"].nunique(),
            "MAE": mean_absolute_error(y_true, y_pred),
            "RMSE": np.sqrt(mean_squared_error(y_true, y_pred)),
            "R2": r2_score(y_true, y_pred)
        }
        
        pred = test_df[[
            "formulation_id", "permeable_cpa", "permeable_conc",
            "sugar_cpa", "sugar_conc", "time_label",
            "storage_day", "cell_viability"
        ]].copy()
        pred["test_name"] = name
        pred["predicted_viability"] = y_pred
        pred["absolute_error"] = np.abs(pred["cell_viability"] - pred["predicted_viability"])
        
        return result, pred
    
    results = []
    predictions = []
    
    for train_cpa, test_cpa in [("EG", "GL"), ("GL", "EG")]:
        train_df = df_long[df_long["permeable_cpa"] == train_cpa].copy()
        test_df = df_long[df_long["permeable_cpa"] == test_cpa].copy()
        res, pred = evaluate(train_df, test_df, f"Train_{train_cpa}_Test_{test_cpa}")
        results.append(res)
        predictions.append(pred)
    
    for sugar in sorted(df_long["sugar_cpa"].unique()):
        train_df = df_long[df_long["sugar_cpa"] != sugar].copy()
        test_df = df_long[df_long["sugar_cpa"] == sugar].copy()
        res, pred = evaluate(train_df, test_df, f"Leave_out_sugar_{sugar}")
        results.append(res)
        predictions.append(pred)
    
    for pconc in sorted(df_long["permeable_conc"].unique()):
        train_df = df_long[df_long["permeable_conc"] != pconc].copy()
        test_df = df_long[df_long["permeable_conc"] == pconc].copy()
        res, pred = evaluate(train_df, test_df, f"Leave_out_permeable_conc_{pconc}")
        results.append(res)
        predictions.append(pred)
    
    results_df = pd.DataFrame(results)
    predictions_df = pd.concat(predictions, ignore_index=True)
    
    results_df["test_family"] = results_df["test_name"].apply(
        lambda x: "CPA_transfer" if "Train_" in x else ("Leave_one_sugar" if "sugar" in x else "Leave_one_concentration")
    )
    
    family_summary = (
        results_df
        .groupby("test_family")[["MAE", "RMSE", "R2"]]
        .agg(["mean", "std"])
        .reset_index()
    )
    
    error_by_test = (
        predictions_df
        .groupby("test_name")["absolute_error"]
        .agg(["mean", "std", "median", "max", "count"])
        .reset_index()
        .sort_values("mean", ascending=False)
    )
    
    save_table(results_df, "Generalization_test_results")
    save_table(predictions_df, "Generalization_test_predictions")
    save_table(family_summary, "Generalization_family_summary")
    save_table(error_by_test, "Generalization_error_by_test")
    
    plt.figure(figsize=(8, 5))
    temp = error_by_test.sort_values("mean", ascending=True)
    plt.barh(temp["test_name"], temp["mean"])
    plt.xlabel("Mean absolute error (%)")
    plt.ylabel("Generalization test")
    plt.title("Generalization error by test")
    save_figure("Figure_generalization_error_by_test")
    
    return results_df, predictions_df, family_summary, error_by_test

def make_manifest():
    files = []
    
    for path in OUTPUT_DIR.rglob("*"):
        if path.is_file():
            files.append({
                "file_name": path.name,
                "relative_path": str(path.relative_to(PROJECT_ROOT)),
                "extension": path.suffix
            })
    
    manifest = pd.DataFrame(files)
    manifest.to_csv(OUTPUT_DIR / "EXPORT_MANIFEST.csv", index=False)
    return manifest

def zip_outputs():
    zip_path = PROJECT_ROOT / "outputs_package.zip"
    
    if zip_path.exists():
        zip_path.unlink()
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for path in OUTPUT_DIR.rglob("*"):
            if path.is_file():
                zipf.write(path, path.relative_to(PROJECT_ROOT))
    
    return zip_path

def main():
    print("Loading data...")
    df_raw = load_data()
    save_table(df_raw, "Input_dataset_loaded")
    
    print("Checking design space...")
    design_summary, missing, extra = design_space_check(df_raw)
    
    print("Engineering formulation-level features...")
    df_features = engineer_features(df_raw)
    save_table(df_features, "Engineered_formulation_level_dataset")
    
    print("Creating long-format ML dataset...")
    df_long = make_long_format(df_features)
    save_table(df_long, "Long_format_ML_dataset")
    
    print("Running feature-set ablation...")
    ablation_results, ablation_predictions, ablation_summary = run_feature_ablation(df_long)
    
    print("Evaluating final model against baselines...")
    final_perf_df, final_predictions_df, final_summary = final_model_vs_baselines(df_long)
    
    print("Computing bootstrap confidence intervals...")
    boot, ci = bootstrap_ci(final_predictions_df)
    
    print("Running SHAP analysis...")
    final_model, shap_importance, shap_direction, continuous_direction, clean_direction = run_shap_analysis(df_long)
    
    print("Running multi-objective design-rule extraction...")
    top_candidates, combo_summary, conc_summary = multiobjective_ranking(df_features)
    
    print("Running sensitivity analysis...")
    sensitivity_df, frequency = sensitivity_analysis(top_candidates)
    
    print("Running generalization tests...")
    gen_results, gen_predictions, gen_family, gen_error = generalization_tests(df_long)
    
    print("Creating manifest...")
    manifest = make_manifest()
    
    print("Creating output ZIP...")
    zip_path = zip_outputs()
    
    print("Pipeline completed.")
    print(f"Outputs folder: {OUTPUT_DIR}")
    print(f"ZIP file: {zip_path}")
    
    return {
        "df_raw": df_raw,
        "df_features": df_features,
        "df_long": df_long,
        "ablation_results": ablation_results,
        "final_perf_df": final_perf_df,
        "final_predictions_df": final_predictions_df,
        "shap_importance": shap_importance,
        "top_candidates": top_candidates,
        "combo_summary": combo_summary,
        "conc_summary": conc_summary,
        "gen_results": gen_results,
        "manifest": manifest
    }

if __name__ == "__main__":
    results = main()
