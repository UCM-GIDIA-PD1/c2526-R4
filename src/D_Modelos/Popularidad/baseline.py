"""
Baseline para predecir la popularidad de los juegos.
Se crean dos modelos, uno que utiliza la media para 
predecir el número de reviews y otro que utiliza la mediana.
Las métricas se registran en Weights & Biases (wandb).
"""
import pandas as pd
from src.utils.config import seed
import wandb
from numpy import sqrt

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error

from src.utils.config import popularity
from src.utils.files import read_file

def transform_baseline(df):
    return df

def predict_baseline_median(model_data, test_df, train_df):
    mediana_train = train_df['recomendaciones_totales'].median()
    return [mediana_train] * len(test_df)

def predict_baseline_mean(model_data, test_df, train_df):
    mean_train = train_df['recomendaciones_totales'].mean()
    return [mean_train] * len(test_df)

def create_popularity_median_baseline(minio):
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Popularidad", 
        name="baseline-median",
        job_type="baseline"
    )

    df = read_file(popularity, minio)
    y_column = "recomendaciones_totales"

    train_df, test_df = train_test_split(df, test_size=0.20, random_state=seed)

    # Calculamos la mediana, que es el valor que va a predecir este baseline
    mediana_train = train_df[y_column].median()

    y_true = test_df[y_column]
    y_pred = [mediana_train] * len(test_df)

    mae = mean_absolute_error(y_true, y_pred)
    rmse = sqrt(mean_squared_error(y_true, y_pred))
    medae = median_absolute_error(y_true, y_pred)

    wandb.log({
        "test_mae": mae,
        "test_rmse": rmse,
        "medae": medae
    })

    print(f"Mediana: {mediana_train}")
    print(f"MAE: {mae:.2f}")
    
    run.finish()

def create_popularity_mean_baseline(minio):
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Popularidad", 
        name="baseline-mean",
        job_type="baseline"
    )

    df = read_file(popularity, minio)
    y_column = "recomendaciones_totales"

    train_df, test_df = train_test_split(df, test_size=0.20, random_state=seed)

    # Calculamos la media, que es el valor que va a predecir este baseline
    mean_train = train_df[y_column].mean()

    y_true = test_df[y_column]
    y_pred = [mean_train] * len(test_df)

    mae = mean_absolute_error(y_true, y_pred)
    rmse = sqrt(mean_squared_error(y_true, y_pred))
    medae = median_absolute_error(y_true, y_pred)

    wandb.log({
        "test_mae": mae,
        "test_rmse": rmse,
        "medae": medae
    })

    print(f"Media: {mean_train}")
    print(f"MAE: {mae:.2f}")
    
    run.finish()

def main(minio = {"minio_write": False, "minio_read": False}):
    create_popularity_mean_baseline(minio)
    create_popularity_median_baseline(minio)

if __name__ == "__main__":
    main()