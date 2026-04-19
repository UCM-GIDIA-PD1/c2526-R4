"""
Script que entrena un modelo XGBoost para predecir la popularidad de los juegos.
Aplica transformaciones a los datos, optimización de hiperparámetros
con Optuna y registro de métricas con Weights & Biases (wandb).
"""

from src.utils.config import popularity, seed
from src.utils.files import read_file, write_to_file
from src.utils.config import popularidad_xgboost_file, popularidad_xgboost_log_file, models_popularidad_path

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import optuna
import wandb
import xgboost as xgb
import umap
import os

import numpy as np
import pandas as pd

def transform_for_xgboost(df):
    """
    Realiza las transformaciones necesarias en el DataFrame para poder entrenar el modelo XGBoost.
    Elimina columnas innecesarias, aplica PCA a los embeddings de CLIP y transforma tipos de datos.

    Args:
        df (pd.DataFrame): DataFrame con los datos originales.
    
    Returns:
        pd.DataFrame: DataFrame limpio y numérico, listo para el entrenamiento.
    """
    df_clean = df.copy()
    
    # Eliminamos columnas que no aportan información al modelo
    errase_columns = ['id', 'name', 'v_resnet', 'v_convnext']
    df_clean = df_clean.drop(columns=[col for col in errase_columns if col in df_clean.columns])

    # Rellenamos los arrays vacíos o nulos en v_clip con ceros
    zero_vector = np.zeros(512)
    df_clean['v_clip'] = df_clean['v_clip'].apply(
        lambda x: x if isinstance(x, (list, np.ndarray)) else zero_vector
    )
    
    # Extraemos la matriz de características y aplicamos UMAP para reducir la dimensionalidad
    clip_matrix = np.vstack(df_clean['v_clip'].values)

    reducer = umap.UMAP(n_components=10, random_state=seed) 
    clip_reduced = reducer.fit_transform(clip_matrix)
    
    for i in range(10):
        df_clean[f'clip_pca_{i}'] = clip_reduced[:, i] # Aunque pone PCA estoy probando con UMAP que es otra técnica
    
    df_clean = df_clean.drop(columns=['v_clip'])

    # Convertimos todo a numérico
    obj_cols = df_clean.select_dtypes(include=['object']).columns
    for col in obj_cols:
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

    df_clean = df_clean.select_dtypes(include=[np.number])
    df_clean = df_clean.fillna(0)

    return df_clean

def predict_xgboost(model_data, test_df, train_df):
    xgb_vars = [c for c in train_df.columns if c != 'recomendaciones_totales']
    X_test_xgb = test_df[xgb_vars]
    y_pred_raw = model_data.predict(X_test_xgb)
    return y_pred_raw

def predict_xgboost_log(model_data, test_df, train_df):
    xgb_vars = [c for c in train_df.columns if c != 'recomendaciones_totales']
    X_test_xgb = test_df[xgb_vars]
    y_pred_raw = model_data.predict(X_test_xgb)
    y_pred_raw = np.maximum(y_pred_raw, 0)
    return np.expm1(y_pred_raw)

def _get_best_xgboost_params(X_train_full, y_train_target_full, use_log):
    """
    Busca los mejores hiperparámetros para el modelo XGBoost utilizando Optuna.

    Args:
        X_train_full (pd.DataFrame): Variables predictoras de entrenamiento.
        y_train_target_full (pd.Series o np.ndarray): Variable objetivo de entrenamiento.
        use_log (bool): Indica si la variable objetivo está en escala logarítmica.
    
    Returns:
        dict: Diccionario con los mejores parámetros encontrados.
    """
    # Dividimos internamente en conjunto de entrenamiento y validación para Optuna
    X_train_opt, X_val_opt, y_train_opt, y_val_opt = train_test_split(
        X_train_full, y_train_target_full, test_size=0.20, random_state=seed
    )

    def objective(trial):
        param = {
            'n_estimators': trial.suggest_int('n_estimators', 50, 300),
            'max_depth': trial.suggest_int('max_depth', 3, 10),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'random_state': 42,
            'n_jobs': -1
        }

        model = xgb.XGBRegressor(**param)
        model.fit(X_train_opt, y_train_opt)

        y_pred_raw = model.predict(X_val_opt)

        if use_log:
            y_pred_raw = np.maximum(y_pred_raw, 0)
            y_pred = np.expm1(y_pred_raw)
            y_val_real = np.expm1(y_val_opt)
        else:
            y_pred = np.maximum(y_pred_raw, 0)
            y_val_real = y_val_opt

        mae = mean_absolute_error(y_val_real, y_pred)

        wandb.log({
            "optuna_trial": trial.number,
            "test_mae": mae,
            "learning_rate": param['learning_rate'],
            "max_depth": param['max_depth']
        })

        return mae
    
    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=35)
    
    return study.best_params

def _train_xgboost(train_df, test_df, y_variable, minio, use_log=False):
    """
    Realiza el ciclo completo de entrenamiento y evaluación del modelo XGBoost:
    obtención de mejores parámetros, ajuste del modelo final e inferencia sobre el conjunto de test.

    Args:
        train_df (pd.DataFrame): DataFrame de entrenamiento.
        test_df (pd.DataFrame): DataFrame de test.
        y_variable (str): Nombre de la variable objetivo.
        use_log (bool): Si es True, aplica logaritmo a la variable objetivo antes de entrenar.

    Returns:
        tuple: (mae, r2, importances)
               - mae (float): Error Absoluto Medio.
               - r2 (float): Coeficiente de determinación R^2.
               - importances (list): Lista de tuplas (variable, importancia) ordenada de mayor a menor.
    """
    variables = [c for c in train_df.columns if c != y_variable]
    
    X_train_full = train_df[variables]

    if use_log:
        y_train_target_full = np.log1p(train_df[y_variable])
    else:
        y_train_target_full = train_df[y_variable]

    # Búsqueda de los mejores hiperparámetros
    best_params = _get_best_xgboost_params(X_train_full, y_train_target_full, use_log)
    best_params['random_state'] = 42
    best_params['n_jobs'] = -1
    
    # Entrenamiento del modelo final
    final_model = xgb.XGBRegressor(**best_params)
    final_model.fit(X_train_full, y_train_target_full)

    os.makedirs(models_popularidad_path(), exist_ok=True)
    model_name = popularidad_xgboost_log_file if use_log else popularidad_xgboost_file
    write_to_file(final_model, model_name, minio) # CAMBIO MINIO
    print(f"Modelo guardado en {model_name}")

    df_importances = pd.DataFrame({
        'Variable': variables,
        'Importancia': final_model.feature_importances_
    })

    df_importances = df_importances.sort_values(by='Importancia', ascending=False)
    importances = df_importances.values.tolist()
    
    return importances

def create_xgboost_model_popularity(use_log, minio):
    """
    Función principal que orquesta el entrenamiento del modelo XGBoost para la predicción de popularidad.
    Se encarga de inicializar wandb, leer los datos, procesarlos, dividirlos en train/test, 
    entrenar el modelo y mostrar los resultados.

    Args:
        use_log (bool): Si es True, predice sobre el logaritmo de las recomendaciones totales.

    Returns:
        None
    """
    run_name = "xgboost-log" if use_log else "xgboost-normal"
    
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Popularidad",
        name=run_name,
        job_type="model-training"
    )

    df = read_file(popularity, minio)
    y_variable = "recomendaciones_totales"
    
    df = transform_for_xgboost(df)

    train_df, test_df = train_test_split(df, test_size=0.20, random_state=seed)

    importances = _train_xgboost(train_df, test_df, y_variable, minio, use_log)

    print("10 variables más importantes:")
    for var_name, var_importance in importances[:10]:
        print(f"- {var_name}: {var_importance:.4f}")

    run.finish()

def main1(minio = {"minio_write": False, "minio_read": False}):
    create_xgboost_model_popularity(False, minio)
    
def main2(minio = {"minio_write": False, "minio_read": False}):
    create_xgboost_model_popularity(True, minio)

if __name__ == "__main__":
    main1()
    main2()
