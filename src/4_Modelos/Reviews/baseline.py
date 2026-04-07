"""
Baseline para predecir la valoración de un comentario.
Se crea un modelo que utiliza la moda (la clase mayoritaria)
para realizar las predicciones.
Las métricas se registran en Weights & Biases (wandb).
"""
import pandas as pd
import wandb

from src.utils.config import reviews
from src.utils.files import read_file
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_score, recall_score,f1_score


def create_reviews_baseline():

    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Reviews", 
        name="baseline_all_positive",
        job_type="baseline"
    )
    
    df = read_file(reviews)
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

    wandb.log({
        "Accuracy": accuracy,
        "Balanced accuracy": balanced_accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1-score": f1
    })

    run.finish()



def main():
    create_reviews_baseline()

if __name__ == "__main__":
    main()
