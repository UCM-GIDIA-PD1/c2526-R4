"""
Script unificado para evaluar los modelos de popularidad.
Calcula métricas para Baseline, Regresión Lineal y XGBoost en el test_df aislado,
y las registra en W&B en un único run y en una tabla comparativa.
"""
import wandb
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, median_absolute_error

from src.utils.config import popularity, seed
from src.utils.files import read_file
from src.D_Modelos.model_list import models_popularidad

def evaluate_models(minio):
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Popularidad",
        name="model-evaluation",
        job_type="evaluation"
    )

    df_raw = read_file(popularity, minio)
    y_variable = "recomendaciones_totales"

    table = wandb.Table(columns=["Model", "MAE", "RMSE", "MEDAE"])

    for model_name, config in models_popularidad.items():
        df = config["transform_function"](df_raw)

        bins_strat = [-np.inf, 6, 23, 106, 320, np.inf]
        y_binned = pd.cut(df[y_variable], bins=bins_strat, labels=False)
        
        train_df, test_df = train_test_split(df, test_size=0.20, random_state=seed, stratify=y_binned)

        if config["model_path"] is not None:
            model_data = read_file(config["model_path"], minio)
        else:
            model_data = None

        y_real = test_df[y_variable]
        y_pred = config["prediction_function"](model_data, test_df, train_df)

        y_pred = np.maximum(y_pred, 0)

        mae = mean_absolute_error(y_real, y_pred)
        rmse = root_mean_squared_error(y_real, y_pred)
        medae = median_absolute_error(y_real, y_pred)

        table.add_data(model_name, mae, rmse, medae)

    wandb.log({"comparative_table": table})

    run.finish()


def main(minio = {"minio_write": False, "minio_read": False}):
    evaluate_models(minio)

if __name__ == "__main__":
    main()