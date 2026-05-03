import wandb
import pandas as pd
import importlib

from sklearn.model_selection import train_test_split

from src.utils.config import seed
from src.D_Modelos.Precios.utils.utils import read_prices, read_new_data, get_metrics
from src.utils.files import read_file
from src.D_Modelos.model_list import models_precios, best_prices_model_retrained
from src.D_Modelos.Precios.xgboost_model import unpack_embeddings

def evaluate_models(minio):
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios",
        name="model-evaluation",
        job_type="evaluation"
    )

    df_raw = read_prices(minio)
    y_variable = "price_range"

    table = wandb.Table(columns=["Model", "accuracy", "f1-score", "precision", "recall"])

    for model_name, config in models_precios.items():
        df = config["transform_function"](df_raw)

        train_df, test_df = train_test_split(df, test_size=0.20, random_state=seed, stratify=df[y_variable])

        if config["model_path"] != None:
            model_data = read_file(config["model_path"], minio)
        else:
            model_data = None

        y_real = test_df[y_variable]
        y_pred = config["prediction_function"](model_data, test_df, train_df)

        metrics_dict = get_metrics(y_real, y_pred)

        table.add_data(
            model_name,
            metrics_dict['accuracy'],
            metrics_dict['f1-score'],
            metrics_dict['precision'],
            metrics_dict['recall']
        )
    
    df_raw_new = read_new_data(minio)
    df = best_prices_model_retrained["transform_function"](df_raw_new)
    
    train_df = None
    test_df = df
    
    model_data = read_file(best_prices_model_retrained["model_path"], minio)
    
    y_real = df[y_variable]
    y_pred = best_prices_model_retrained["prediction_function"](model_data, test_df, train_df)
    
    metrics_dict = get_metrics(y_real, y_pred)

    table.add_data(
        "K-NN Complete Clusters Retrained",
        metrics_dict['accuracy'],
        metrics_dict['f1-score'],
        metrics_dict['precision'],
        metrics_dict['recall']
    )

    wandb.log({"comparative_table": table})
    print("Evaluación completada. Resultados en W&B.")
    run.finish()


def main(minio = {"minio_write": False, "minio_read": False}):
    evaluate_models(minio)

if __name__ == "__main__":
    main()
