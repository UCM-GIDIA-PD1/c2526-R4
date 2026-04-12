"""
Script unificado para evaluar los modelos de popularidad.
Calcula métricas para Baseline, Regresión Lineal y XGBoost en el test_df aislado,
y las registra en W&B en un único run y en una tabla comparativa.
"""
import wandb
import pandas as pd
from math import sqrt
import importlib

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

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

    table = wandb.Table(columns=["Model", "MAE", "RMSE", "R2"])

    for model_name, config in models_popularidad.items():
        df = config["transform_function"](df_raw)

        bins_strat = [-1, 10, 100, 1000, 10000, float('inf')]
        y_binned = pd.cut(df[y_variable], bins=bins_strat, labels=False)
        train_df, test_df = train_test_split(df, test_size=0.20, random_state=seed, stratify=y_binned)

        if config["model_path"] != None:
            model_data = read_file(config["model_path"], minio)
        else:
            model_data = None

        y_real = test_df[y_variable]
        y_pred = config["prediction_function"](model_data, test_df, train_df)

        mae = mean_absolute_error(y_real, y_pred)
        rmse = sqrt(mean_squared_error(y_real, y_pred))
        r2 = r2_score(y_real, y_pred)

        table.add_data(model_name, mae, rmse, r2)

    wandb.log({"comparative_table": table})
    print("Evaluación completada. Resultados en W&B.")

    run.finish()


def main(minio = {"minio_write": False, "minio_read": False}):
    evaluate_models(minio)

if __name__ == "__main__":
    main()
