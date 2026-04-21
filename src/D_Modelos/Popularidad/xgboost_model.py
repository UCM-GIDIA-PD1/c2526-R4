"""
Script que entrena un modelo XGBoost para predecir la popularidad de los juegos.
Aplica transformaciones a los datos, optimización de hiperparámetros
con Optuna y registro de métricas con Weights & Biases (wandb).
"""

import os
import numpy as np
import pandas as pd
import xgboost as xgb
import wandb
import optuna

from src.utils.config import popularity, seed
from src.utils.files import read_file, write_to_file
from src.utils.config import popularidad_xgboost_file, popularidad_xgboost_log_file, models_popularidad_path
from src.utils.config import popularidad_xgboost_nomulti_file, popularidad_xgboost_log_nomulti_file
from src.D_Modelos.Popularidad.utils import clean_df, create_stratified_bins

from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer


def transform_xgboost(df):
    """Transforma los datos usando la configuración por defecto para XGBoost."""
    # Por defecto usamos avoid_multicol=True para la evaluación final
    return clean_df(df, avoid_multicol=True)

def predict_xgboost(model_data, test_df, train_df=None):
    """Realiza la predicción consumiendo el diccionario extraído del .pkl"""
    modelo_final = model_data["model"]
    X_test = test_df.drop(columns=["recomendaciones_totales"], errors='ignore')
    preds = np.maximum(modelo_final.predict(X_test), 0)
    return preds

def get_clip_matrix(X):
    # Transforma la serie de listas/arrays en una matriz 2D.
    return np.vstack(X.iloc[:, 0].values)

def build_standard_estimator(preprocessor, reg_params, use_log):
    """
    Construye y devuelve un estimador estándar de XGBoost
    insertado en un pipeline con sus transformadores.
    """
    params = reg_params.copy()
    if not use_log:
        params['objective'] = 'reg:tweedie'
        params.setdefault('tweedie_variance_power', 1.5)

    reg_base = Pipeline([
        ('prep', preprocessor), 
        ('xgb_reg', xgb.XGBRegressor(**params))
    ])

    if use_log:
        return TransformedTargetRegressor(regressor=reg_base, func=np.log1p, inverse_func=np.expm1)
    return reg_base

def get_best_hyperparameters(X_train, y_train, y_binned_train, preprocessor, use_log):
    """
    Ejecuta un estudio de Optuna para encontrar los mejores hiperparámetros 
    minimizando el RMSE.
    """
    def objective(trial):
        param = {
            'n_estimators': trial.suggest_int('n_estimators', 50, 300),
            'max_depth': trial.suggest_int('max_depth', 3, 10),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'random_state': seed,
            'n_jobs': -1
        }
        
        if not use_log:
            param['tweedie_variance_power'] = trial.suggest_float('tweedie_variance_power', 1.1, 1.9)

        model = build_standard_estimator(preprocessor, param, use_log)
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        cv_splits = list(cv.split(X_train, y_binned_train))
        
        cv_results = cross_validate(
            model, X_train, y_train, 
            scoring='neg_root_mean_squared_error', 
            cv=cv_splits, n_jobs=1
        )
        
        return -cv_results['test_score'].mean()

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=30) 
    return study.best_params


def run_experiment(df_raw, config, minio, hyperparameters=None):
    """
    Ejecuta el pipeline completo y registra los resultados en Weights & Biases.
    """
    avoid_multicol = config.get("avoid_multicol", True)
    use_log = config.get("use_log", True)

    multicol_suffix = "no_multicol" if avoid_multicol else "with_multicol"
    log_suffix = "log" if use_log else "raw"
    run_name = f"xgboost-{multicol_suffix}-{log_suffix}"
    
    if avoid_multicol:
        model_path = popularidad_xgboost_log_nomulti_file if use_log else popularidad_xgboost_nomulti_file
    else:
        model_path = popularidad_xgboost_log_file if use_log else popularidad_xgboost_file

    run = wandb.init(
        entity="pd1-c2526-team4", 
        project="Popularidad", 
        name=run_name,
        job_type="model-training",
        config=config
    )

    print(f"Iniciando experimento: {run_name} ---")
    
    df_prep = clean_df(df_raw, avoid_multicol)
    X = df_prep.drop(columns=["recomendaciones_totales"])
    y = df_prep["recomendaciones_totales"]
    
    y_binned = create_stratified_bins(y, n_bins=5, random_state=seed)
    X_train, X_test, y_train, y_test, y_binned_train, _ = train_test_split(
        X, y, y_binned, test_size=0.2, stratify=y_binned, random_state=seed
    )
    
    numeric_columns = [col for col in X.columns if col != 'v_clip']
    clip_pipe = Pipeline([
        ('extractor', FunctionTransformer(get_clip_matrix, validate=False)),
        ('pca', PCA(n_components=10, random_state=seed))
    ])
    preprocessor = ColumnTransformer(transformers=[
        ('clip_pca', clip_pipe, ['v_clip']),
        ('numeric', 'passthrough', numeric_columns)
    ], remainder='drop')

    model_data = None
    try:
        model_data = read_file(model_path, minio)
    except Exception:
        model_data = None
    
    if model_data is not None:
        print(f"Cargando modelo existente de {model_path}...")
        modelo_final = model_data["model"]
        best_params = model_data.get("hyperparameters", {})
    else:
        print("No se encontró pkl. Iniciando entrenamiento...")
        if hyperparameters:
            best_params = hyperparameters.copy()
        else:
            best_params = get_best_hyperparameters(X_train, y_train, y_binned_train, preprocessor, use_log)

        best_params.update({'random_state': seed, 'n_jobs': -1})

        modelo_final = build_standard_estimator(preprocessor, best_params, use_log)
        modelo_final.fit(X_train, y_train)

        # Guardado del diccionario completo para futuras ejecuciones
        os.makedirs(models_popularidad_path(), exist_ok=True)
        write_to_file({"model": modelo_final, "hyperparameters": best_params}, model_path, minio)
        print(f"Modelo guardado exitosamente en {model_path}")

    wandb.config.update({"params": best_params})
    preds = np.maximum(modelo_final.predict(X_test), 0)
    
    mae = mean_absolute_error(y_test, preds)
    rmse = root_mean_squared_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    
    print(f"Resultados: MAE: {mae:.4f} | RMSE: {rmse:.4f} | R2: {r2:.4f}")

    wandb.log({
        "test_mae": mae, 
        "test_rmse": rmse,
        "test_r2": r2
    })
    
    run.finish() # Cierre estándar de WandB


def main(minio={"minio_write": False, "minio_read": False}):
    df_raw = read_file(popularity, minio)
    
    my_config = {
        "avoid_multicol": True,
        "use_log": True
    }
    
    run_experiment(df_raw, config=my_config, minio=minio)

if __name__ == "__main__":
    main()