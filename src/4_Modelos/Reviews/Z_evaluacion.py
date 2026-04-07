"""
Script unificado para evaluar los modelos del problema de reviews de predecir si
una valoración es positiva o negativa.
"""

from src.utils.files import read_file
from src.utils.config import reviews_logistic_regression_gridsearch_file, reviews_logistic_regression_optuna_file
from src.utils.config import reviews
from utils_modelo_reviews.preprocesamiento import train_val_test_split
from logistic_regression import preprocess

import wandb
from tqdm import tqdm

from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_score, recall_score,f1_score
from sklearn.model_selection import train_test_split



def evaluate_models():
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Reviews",
        name="model-evaluation",
        job_type="evaluation"
    )
    tqdm.pandas(desc="Limpiando texto")
    df = read_file(reviews)
    
    # Modelo baseline (moda)
    y_column = "is_positive"

    train_df, test_df = train_test_split(df, test_size=0.20, random_state=42)

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
    
    
if __name__ == "__main__":
    evaluate_models()