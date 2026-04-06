"""
Script unificado para evaluar los modelos del problema de reviews de predecir si
una valoración es positiva o negativa.
"""
import os
import numpy as np
import pandas as pd
import wandb
import joblib

from src.utils.config import reviews
from src.utils.files import read_file
from utils_modelo_reviews.preprocesamiento import train_val_test_split

from tqdm import tqdm

from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_score, recall_score,f1_score

from logistic_regression import preprocess


def evaluate_models():
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Reviews",
        name="model-evaluation",
        job_type="evaluation"
    )
    tqdm.pandas(desc="Limpiando texto")
    df = read_file(reviews)
    
    X, y = preprocess(df)
    
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)
    
    X_train_val = np.concatenate([X_train, X_val])
    y_train_val = np.concatenate([y_train, y_val])
    
    model_path = "data/models/logistic_regression_optuna.pkl"
    
    if os.path.exists(model_path):
        best_logistic_model = joblib.load(model_path)
        
        y_pred_test = best_logistic_model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred_test)
        f1 = f1_score(y_test, y_pred_test)
        balanced_accuracy = balanced_accuracy_score(y_test, y_pred_test)
        recall= recall_score(y_test, y_pred_test)
        precision=  precision_score(y_test, y_pred_test)
        
        table = wandb.Table(columns=["Model", "accuracy", "f1", "balanced_accuracy", "recall", "precision"])
        table.add_data("logistic_regression_optuna", accuracy, f1, balanced_accuracy, recall, precision)
        
        
        wandb.log({"comparative_table": table})
        print("Evaluación completada. Resultados en W&B.")

    run.finish()
    
    
if __name__ == "__main__":
    evaluate_models()