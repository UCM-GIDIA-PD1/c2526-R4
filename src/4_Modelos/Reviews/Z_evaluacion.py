"""
Script unificado para evaluar los modelos del problema de reviews de predecir si
una valoración es positiva o negativa.
"""
import os
import numpy as np
import pandas as pd
import wandb
import joblib
import nltk

from utils_modelo_reviews.preprocesamiento import train_val_test_split, read_reviews

from tqdm import tqdm

from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_score, recall_score,f1_score
from sklearn.model_selection import train_test_split

from logistic_regression import preprocess
from naive_bayes_CV import preprocesar_texto as preprocesar_cv
from naive_bayes_CV import calcular_metricas
from naive_bayes_CV import train_best_model  as train_naivebayes_cv
from naive_bayes_TFIDF import preprocesar_texto as preprocesar_tfidf
from naive_bayes_TFIDF import train_best_model  as train_naivebayes_tfidf


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

    train_df, test_df = train_test_split(df, test_size=0.30, random_state=42)

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
    
    model_path_optuna = "models/reviews/logistic_regression_optuna.pkl"
    
    if os.path.exists(model_path_optuna):
        best_logistic_model = joblib.load(model_path_optuna)
        
        y_pred_test = best_logistic_model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred_test)
        f1 = f1_score(y_test, y_pred_test)
        balanced_accuracy = balanced_accuracy_score(y_test, y_pred_test)
        recall= recall_score(y_test, y_pred_test)
        precision=  precision_score(y_test, y_pred_test)
        

        table.add_data("logistic_regression_optuna", accuracy, f1, balanced_accuracy, recall, precision)
        
    model_path_gridsearch = "models/reviews/logistic_regression_gridsearch.pkl"
    
    if os.path.exists(model_path_gridsearch):
        best_logistic_model = joblib.load(model_path_gridsearch)
        
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
    
    
if __name__ == "__main__":
    evaluate_models()