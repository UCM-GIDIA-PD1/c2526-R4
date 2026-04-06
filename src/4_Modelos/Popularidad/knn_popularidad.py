"""
Dado popularidad.parquet, ejecuta el modelo óptimo para predecir recomendaciones_totales
"""

from src.utils.config import popularity
from src.utils.files import read_file

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, mean_squared_log_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, PowerTransformer
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
import os
import joblib

import wandb

import numpy as np
import pandas as pd

BEST_KNN_PARAMS = {
    "n_neighbors": 20,
    "weights": "distance",
    "p": 1
}

VARIABLES_GANADORAS = [
    'Free To Play', 'yt_score', 'Steam Trading Cards', 'price_overview', 
    'Steam Cloud', 'num_languages', 'Steam Achievements', 'RPG', 
    'Custom Volume Controls', 'Simulation', 'release_year', 'Co-op', 
    'Multi-player', 'Shared/Split Screen', 'total_games_by_publisher'
]

def _transform_for_knn(df):
    """
    Preprocesamiento limpio y directo. Solo conserva las variables
    ganadoras y la variable objetivo, forzando los tipos numéricos.
    """
    cols_to_keep = VARIABLES_GANADORAS + ['recomendaciones_totales']
    df_clean = df[[c for c in cols_to_keep if c in df.columns]].copy()

    # Forzamos numéricos y rellenamos nulos con 0
    for col in VARIABLES_GANADORAS:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)

    return df_clean

def create_knn_model_popularity():
    """
    Orquesta el entrenamiento del mejor modelo KNN (solo tabular) y su subida a wandb.
    """
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Popularidad",
        name="knn-model-log",
        job_type="knn-model-log",
        config={
            "modelo": "KNN_POPULARIDAD", 
            "params": BEST_KNN_PARAMS, 
            "variables": VARIABLES_GANADORAS
        }
    )

    df_raw = read_file(popularity)
    print("Aplicando transformaciones a los datos...")
    df_prepared = _transform_for_knn(df_raw)
    
    X = df_prepared[VARIABLES_GANADORAS]
    y = df_prepared['recomendaciones_totales']

    bins_strat = [-1, 10, 100, 1000, 10000, float('inf')]
    y_binned = pd.cut(y, bins=bins_strat, labels=False)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y_binned
    )

    todas_sesgadas = ['price_overview', 'num_languages', 'total_games_by_publisher']
    cols_sesgadas = [c for c in VARIABLES_GANADORAS if c in todas_sesgadas]
    cols_binarias = [c for c in VARIABLES_GANADORAS if set(X_train[c].dropna().unique()).issubset({0, 1, 0.0, 1.0})]
    cols_normales = [c for c in VARIABLES_GANADORAS if c not in cols_sesgadas + cols_binarias]

    preprocessor = ColumnTransformer(transformers=[
        ('sesgadas', PowerTransformer(method='yeo-johnson'), cols_sesgadas),
        ('normales', StandardScaler(), cols_normales),
        ('binarias', 'passthrough', cols_binarias)
    ], remainder='drop')

    final_model = TransformedTargetRegressor(
        regressor=Pipeline([
            ('prep', preprocessor),
            ('knn', KNeighborsRegressor(**BEST_KNN_PARAMS, n_jobs=-1))
        ]),
        func=np.log1p,
        inverse_func=np.expm1
    )

    print("Entrenando el modelo KNN definitivo...")
    final_model.fit(X_train, y_train)

    y_pred = np.clip(final_model.predict(X_test), 0, None)
    
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    rmsle = np.sqrt(mean_squared_log_error(y_test, y_pred))

    print(f"\nResultados Test:")
    print(f"MAE:   {mae:.4f}")
    print(f"RMSE:  {rmse:.4f}")
    print(f"R2:    {r2:.4f}")
    print(f"RMSLE: {rmsle:.4f}")

    wandb.log({
        "test_mae": mae,
        "test_rmse": rmse,
        "test_r2": r2,
        "test_rmsle": rmsle
    })

    os.makedirs('models/popularidad', exist_ok=True)
    model_path = "models/popularidad/knn_model_log.pkl"
    joblib.dump(final_model, model_path)
    print(f"\nModelo guardado exitosamente en {model_path}")

    run.finish()

if __name__ == "__main__":
    create_knn_model_popularity()