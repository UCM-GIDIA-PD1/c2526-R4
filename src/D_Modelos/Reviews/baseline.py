"""
Baseline para predecir la valoración de un comentario.
Se crea un modelo que utiliza la moda (la clase mayoritaria)
para realizar las predicciones.
Las métricas se registran en Weights & Biases (wandb).
"""
import pandas as pd
import wandb

from src.utils.config import reviews, seed
from src.utils.files import read_file
from sklearn.model_selection import train_test_split
from src.D_Modelos.Reviews.utils.utils import get_metrics

class_names = ["Negativo", "Positivo"]

def create_reviews_baseline(minio):

    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Reviews", 
        name="baseline_all_positive",
        job_type="baseline"
    )
    
    df = read_file(reviews, minio)
    y_column = "is_positive"

    train_df, test_df = train_test_split(df, test_size=0.30, random_state=seed)

    mayority = train_df[y_column].value_counts().idxmax()

    y_true = test_df[y_column]
    y_pred = [mayority] * len(y_true)

    cm_path = 'models/reviews/graficos/confusionMatrix/baseline.png'

    metricas = get_metrics(
        y_true, 
        y_pred,
        classes=class_names,
        img_path=cm_path, 
        download_images=True
    )

    run.log(metricas)
    run.finish()



def main(minio = {"minio_write": False, "minio_read": False}):
    create_reviews_baseline(minio)

if __name__ == "__main__":
    main()
