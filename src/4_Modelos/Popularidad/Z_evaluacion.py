"""
Script unificado para evaluar los modelos de popularidad.
Calcula métricas para Baseline, Regresión Lineal y XGBoost en el test_df aislado,
y las registra en W&B en un único run y en una tabla comparativa.
"""

from src.utils.config import popularity
from src.utils.files import read_file
from src.utils.config import popularidad_xgboost_file, popularidad_xgboost_log_file, popularidad_mlp_file
from src.utils.config import popularidad_linear_regression_file, popularidad_linear_regression_log_file, popularidad_knn_log_file

from linear_regresion_log import transform_for_linear_regresion
from xgboost_popularidad import _transform_for_xgboost
from mlp_popularidad import _preprocess_test
from knn_popularidad import _transform_for_knn, VARIABLES_GANADORAS

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import os
import joblib
import statsmodels.api as sm

import wandb

import numpy as np
import pandas as pd
from math import sqrt
from src.utils.config import seed

def evaluate_models():
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Popularidad",
        name="model-evaluation",
        job_type="evaluation"
    )

    df_raw = read_file(popularity)
    y_variable = "recomendaciones_totales"

    # Modelo base (Baseline)
    train_df_raw, test_df_raw = train_test_split(df_raw, test_size=0.20, random_state=seed)
    mediana_train = train_df_raw[y_variable].median()
    y_test_real = test_df_raw[y_variable]
    y_pred_baseline = np.full_like(y_test_real, mediana_train, dtype=float)

    mae_baseline = mean_absolute_error(y_test_real, y_pred_baseline)
    rmse_baseline = sqrt(mean_squared_error(y_test_real, y_pred_baseline))
    r2_baseline = r2_score(y_test_real, y_pred_baseline)

    table = wandb.Table(columns=["Model", "MAE", "RMSE", "R2"])
    table.add_data("Baseline (Median)", mae_baseline, rmse_baseline, r2_baseline)
    
    metrics = {
        "baseline_mae": mae_baseline,
        "baseline_rmse": rmse_baseline,
        "baseline_r2": r2_baseline,
    }

    # Evaluación de la Regresión Lineal
    df_lr = transform_for_linear_regresion(df_raw)
    train_df_lr, test_df_lr = train_test_split(df_lr, test_size=0.20, random_state=seed)

    for use_log, model_path, model_name in [
        (False, popularidad_linear_regression_file, "Linear Regression (Normal)"),
        (True, popularidad_linear_regression_log_file, "Linear Regression (Log)")
    ]:
        lr_data = read_file(model_path, {"minio_write": False, "minio_read": False}) # CAMBIAR MINIO
        if lr_data:
            lr_model = lr_data["model"]
            lr_vars = lr_data["selected_variables"]
            
            X_test_lr = sm.add_constant(test_df_lr[lr_vars], has_constant='add')
            y_pred_raw_lr = lr_model.predict(X_test_lr)
            
            if use_log:
                y_pred_lr = np.expm1(y_pred_raw_lr)
            else:
                y_pred_lr = y_pred_raw_lr
                
            mae_lr = mean_absolute_error(y_test_real, y_pred_lr)
            rmse_lr = sqrt(mean_squared_error(y_test_real, y_pred_lr))
            r2_lr = r2_score(y_test_real, y_pred_lr)
            
            prefix = "lr_log_" if use_log else "lr_"
            metrics.update({
                f"{prefix}mae": mae_lr,
                f"{prefix}rmse": rmse_lr,
                f"{prefix}r2": r2_lr,
            })
            table.add_data(model_name, mae_lr, rmse_lr, r2_lr)

    # Evaluación de XGBoost
    df_xgb = _transform_for_xgboost(df_raw)
    train_df_xgb, test_df_xgb = train_test_split(df_xgb, test_size=0.20, random_state=seed)

    for use_log, model_path, model_name in [
        (False, popularidad_xgboost_file, "XGBoost (Normal)"),
        (True, popularidad_xgboost_log_file, "XGBoost (Log)")
    ]:
        xgb_model = read_file(model_path, {"minio_write": False, "minio_read": False}) # CAMBIAR MINIO
        if xgb_model:
            xgb_vars = [c for c in train_df_xgb.columns if c != y_variable]
            
            X_test_xgb = test_df_xgb[xgb_vars]
            y_pred_raw_xgb = xgb_model.predict(X_test_xgb)
            
            if use_log:
                y_pred_raw_xgb = np.maximum(y_pred_raw_xgb, 0)
                y_pred_xgb = np.expm1(y_pred_raw_xgb)
            else:
                y_pred_xgb = np.maximum(y_pred_raw_xgb, 0)
                
            mae_xgb = mean_absolute_error(y_test_real, y_pred_xgb)
            rmse_xgb = sqrt(mean_squared_error(y_test_real, y_pred_xgb))
            r2_xgb = r2_score(y_test_real, y_pred_xgb)
            
            prefix = "xgb_log_" if use_log else "xgb_"
            metrics.update({
                f"{prefix}mae": mae_xgb,
                f"{prefix}rmse": rmse_xgb,
                f"{prefix}r2": r2_xgb,
            })
            table.add_data(model_name, mae_xgb, rmse_xgb, r2_xgb)

    # Evaluación de MLP (Red Neuronal)
    mlp_data = read_file(popularidad_mlp_file, {"minio_write": False, "minio_read": False}) # CAMBIAR MINIO
    if mlp_data:
        mlp_model = mlp_data["model"]
        transformers_dict = mlp_data["transformers"]
        y_min = mlp_data["y_train_min"]
        y_max = mlp_data["y_train_max"]
        
        X_test_mlp, _ = _preprocess_test(test_df_raw, transformers_dict)
        
        y_pred_mlp = mlp_model.predict(X_test_mlp)
        
        # Limitar (clip) y aplicar la transformación inversa usando numpy clip
        y_pred_clipped_mlp = np.clip(y_pred_mlp, y_min, y_max)
        y_pred_real_mlp = transformers_dict['pt1'].inverse_transform(y_pred_clipped_mlp.reshape(-1, 1)).flatten()
        
        mae_mlp = mean_absolute_error(y_test_real, y_pred_real_mlp)
        rmse_mlp = sqrt(mean_squared_error(y_test_real, y_pred_real_mlp))
        r2_mlp = r2_score(y_test_real, y_pred_real_mlp)
        
        metrics.update({
            "mlp_mae": mae_mlp,
            "mlp_rmse": rmse_mlp,
            "mlp_r2": r2_mlp,
        })
        table.add_data("MLP", mae_mlp, rmse_mlp, r2_mlp)

    # Evaluación de KNN
    knn_model = read_file(popularidad_knn_log_file, {"minio_write": False, "minio_read": False}) # CAMBIAR MINIO
    if knn_model:
        df_knn = _transform_for_knn(df_raw)
        
        y_knn = df_knn['recomendaciones_totales']
        bins_strat = [-1, 10, 100, 1000, 10000, float('inf')]
        y_binned = pd.cut(y_knn, bins=bins_strat, labels=False)
        
        _, test_df_knn = train_test_split(df_knn, test_size=0.20, random_state=seed, stratify=y_binned)
        
        X_test_knn = test_df_knn[VARIABLES_GANADORAS]
        y_test_real_knn = test_df_knn['recomendaciones_totales']
        
        y_pred_knn = knn_model.predict(X_test_knn)
        y_pred_knn = np.clip(y_pred_knn, 0, None)
        
        mae_knn = mean_absolute_error(y_test_real_knn, y_pred_knn)
        rmse_knn = sqrt(mean_squared_error(y_test_real_knn, y_pred_knn))
        r2_knn = r2_score(y_test_real_knn, y_pred_knn)
        
        metrics.update({
            "knn_log_mae": mae_knn,
            "knn_log_rmse": rmse_knn,
            "knn_log_r2": r2_knn,
        })
        table.add_data("KNN (Log)", mae_knn, rmse_knn, r2_knn)

    wandb.log(metrics)
    wandb.log({"comparative_table": table})
    print("Evaluación completada. Resultados en W&B.")

    run.finish()


def main():
    evaluate_models()

if __name__ == "__main__":
    main()
