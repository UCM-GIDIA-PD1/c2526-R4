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

from src.D_Modelos.Popularidad.linear_regression import get_clip_matrix, select_features
from src.D_Modelos.Popularidad.knn import slice_umap
from src.D_Modelos.Popularidad.mlp import get_image_matrix, cast_to_float32, safe_expm1, build_keras_heavyweight

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

    for model_name, info in models_popularidad.items():
        print(f"Evaluando: {model_name}...")
        
        if info["type"] == "class":
            model = info["class_ref"](minio=minio, **info.get("kwargs", {}))
            
            metricas = model.evaluate(df_raw, config=info["config"])
            table.add_data(model_name, metricas["mae"], metricas["rmse"], metricas["medae"])
            
        elif info["type"] == "baseline":
            train_df, test_df = train_test_split(df_raw, test_size=0.20, random_state=seed)
            
            y_real = test_df[y_variable]
            y_pred = info["prediction_function"](None, test_df, train_df)

            mae = mean_absolute_error(y_real, y_pred)
            rmse = root_mean_squared_error(y_real, y_pred)
            medae = median_absolute_error(y_real, y_pred)

            table.add_data(model_name, mae, rmse, medae)

    wandb.log({"comparative_table": table})
    print("\nEvaluación completada.")
    run.finish()


def main(minio = {"minio_write": False, "minio_read": False}):
    evaluate_models(minio)

if __name__ == "__main__":
    main()