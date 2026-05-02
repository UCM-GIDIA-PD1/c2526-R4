"""
Script unificado para evaluar los modelos del problema de reviews de predecir si
una valoración es positiva o negativa.
"""

import numpy as np
import pandas as pd
import wandb
import nltk

from src.utils.files import read_file
from src.utils.config import seed

from src.D_Modelos.Reviews.utils.preprocesamiento import read_reviews, read_new_data

import wandb
from tqdm import tqdm
from sklearn.model_selection import train_test_split

from src.D_Modelos.model_list import models_reviews, best_reviews_model_retrained
from src.D_Modelos.Reviews.utils.utils import get_metrics

class_names = ["Negativo", "Positivo"]

def evaluate_models(minio):
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Reviews",
        name="model-evaluation",
        job_type="evaluation"
    )

    df_raw = read_reviews(minio)
    y_variable = "is_positive"

    table = wandb.Table(columns=["Model", "Accuracy", "F1-score","Balanced accuracy", "Recall","Precision"])

    for model_name, config in models_reviews.items():
        df = config["transform_function"](df_raw)

        train_df, test_df = train_test_split(df, test_size=0.20, random_state=seed, stratify=df[y_variable])

        if config["model_path"] != None:
            model_data = read_file(config["model_path"], minio)
        else:
            model_data = None

        y_real = test_df[y_variable]
        y_pred = config["prediction_function"](model_data, test_df, train_df)

        metrics_dict = get_metrics(y_real, y_pred, class_names)

        table.add_data(
            model_name,
            metrics_dict['accuracy'],
            metrics_dict['f1-score'],
            metrics_dict['balanced_accuracy'],
            metrics_dict['recall'],
            metrics_dict['precision']
            metrics_dict['confusion_matrix']
        )

    df_raw_new = read_new_data(minio)
    df = best_reviews_model_retrained["transform_function"](df_raw_new)
    
    train_df = None
    test_df = df
    
    model_data = read_file(best_reviews_model_retrained["model_path"], minio)
    
    y_real = df[y_variable]
    y_pred = best_reviews_model_retrained["prediction_function"](model_data, test_df, train_df)
    
    metrics_dict = get_metrics(y_real, y_pred)

    table.add_data(
        "Logistic Regression Retrained",
        metrics_dict['accuracy'],
        metrics_dict['f1-score'],
        metrics_dict['balanced_accuracy'],
        metrics_dict['recall'],
        metrics_dict['precision']
    )
    
    wandb.log({"comparative_table": table})
    print("Evaluación completada. Resultados en W&B.")
    run.finish()
    
def main(minio = {"minio_write": False, "minio_read": False}):
    evaluate_models(minio)

if __name__ == "__main__":
    main()
