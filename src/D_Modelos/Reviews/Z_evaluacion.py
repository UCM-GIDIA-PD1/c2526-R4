"""
Script unificado para evaluar los modelos del problema de reviews de predecir si
una valoración es positiva o negativa.
"""

import numpy as np
import pandas as pd
import wandb
import nltk

from src.utils.files import read_file
from src.utils.config import reviews_logistic_regression_gridsearch_file, reviews_logistic_regression_optuna_file
from src.utils.config import reviews
from src.utils.config import seed

from src.D_Modelos.Reviews.utils.preprocesamiento import train_val_test_split, read_reviews

import wandb
from tqdm import tqdm

from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_score, recall_score,f1_score
from sklearn.model_selection import train_test_split

from src.D_Modelos.model_list import models_reviews
from src.D_Modelos.Reviews.utils.utils import get_metrics

def evaluate_models():
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Reviews",
        name="model-evaluation",
        job_type="evaluation"
    )
    tqdm.pandas(desc="Limpiando texto")
    df = read_reviews()
    
    # Modelo baseline (moda)
    y_column = "is_positive"

    train_df, test_df = train_test_split(df, test_size=0.30, random_state=seed)

    mayority = train_df[y_column].value_counts().idxmax()

    y_true = test_df[y_column]
    y_pred = [mayority] * len(y_true)


    accuracy = accuracy_score(y_true, y_pred)
    balanced_accuracy = balanced_accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred)
    recall = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)
    
    table = wandb.Table(columns=["Model", "Accuracy", "F1-score", "Balanced accuracy", "Recall", "Precision"])
    table.add_data("baseline-mode", accuracy, f1, balanced_accuracy, recall, precision)
    
    # Modelos naive bayes 
    # CountVectorizer
    df = read_reviews()
    reviews = df["text"].to_list() # minusculas y solo caracteres alphanumericos y signos comunes de puntuacion
    labels = df["is_positive"].to_list()

    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(reviews, labels)
    X_train, X_val, X_test = preprocesar_cv(X_train, X_val, X_test)
    X_train_full = X_train + X_val
    y_train_full = y_train + y_val

    best_naivebayes_cv = train_naivebayes_cv(X_train_full, y_train_full)
    y_pred = best_naivebayes_cv.predict(X_test)
    accuracy, balanced_accuracy, precision, recall, f1 = calcular_metricas(y_test, y_pred)
    table.add_data("naivebayes_cv", accuracy, f1, balanced_accuracy, recall, precision)

    # Tf-idf
    df = read_reviews()
    reviews = df["text"].to_list() # minusculas y solo caracteres alphanumericos y signos comunes de puntuacion
    labels = df["is_positive"].to_list()

    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(reviews, labels)
    X_train, X_val, X_test = preprocesar_tfidf(X_train, X_val, X_test)
    X_train_full = X_train + X_val
    y_train_full = y_train + y_val
    best_naivebayes_tfidf = train_naivebayes_tfidf(X_train_full, y_train_full)
    y_pred = best_naivebayes_tfidf.predict(X_test)
    accuracy, balanced_accuracy, precision, recall, f1 = calcular_metricas(y_test, y_pred)
    table.add_data("naivebayes_tfidf", accuracy, f1, balanced_accuracy, recall, precision)

    # Modelo de regresión logística
    X, y = preprocess(df)
    
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)
    
    best_logistic_model = read_file(reviews_logistic_regression_optuna_file, {"minio_write": False, "minio_read": False}) # CAMBIAR MINIO
    if best_logistic_model:
        y_pred_test = best_logistic_model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred_test)
        f1 = f1_score(y_test, y_pred_test)
        balanced_accuracy = balanced_accuracy_score(y_test, y_pred_test)
        recall= recall_score(y_test, y_pred_test)
        precision=  precision_score(y_test, y_pred_test)

        table.add_data("logistic_regression_optuna", accuracy, f1, balanced_accuracy, recall, precision)
    
    best_logistic_model = read_file(reviews_logistic_regression_gridsearch_file, {"minio_write": False, "minio_read": False}) # CAMBIAR MINIO
    if best_logistic_model:        
        y_pred_test = best_logistic_model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred_test)
        f1 = f1_score(y_test, y_pred_test)
        balanced_accuracy = balanced_accuracy_score(y_test, y_pred_test)
        recall= recall_score(y_test, y_pred_test)
        precision=  precision_score(y_test, y_pred_test)
        

        table.add_data("logistic_regression_gridsearch", accuracy, f1, balanced_accuracy, recall, precision)   

    wandb.log({"comparative_table": table})
    print("Evaluación completada. Resultados en W&B.")

    run.finish()


def evaluate_models_h(minio):
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

        metrics_dict = get_metrics(y_real, y_pred)

        table.add_data(
            model_name,
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
    evaluate_models_h(minio)

if __name__ == "__main__":
    main()
