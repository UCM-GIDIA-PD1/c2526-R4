"""
Dado popularidad.parquet, ejecuta el modelo óptimo para predecir recomendaciones_totales
"""
import numpy as np
import pandas as pd
import os
import wandb
import optuna

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, mean_squared_log_error
from sklearn.model_selection import train_test_split, KFold, cross_validate
from sklearn.preprocessing import StandardScaler, PowerTransformer
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor

from src.utils.config import popularity
from src.utils.files import read_file, write_to_file
from src.utils.config import popularidad_knn_log_file, models_popularidad_path
from src.utils.config import seed

# HAY QUE PONER LAS VARIABLES QUE SALGAN EN XGBOOST
VARIABLES_GANADORAS = ['commentCountTotal', 'Family Sharing', 'Steam Cloud', 'ema_reviews_publishers', 'Free To Play', 
 'Steam Trading Cards', 'num_languages', 'price_overview', 'Steam Achievements', 'Online Co-op', 
 'yt_score', 'Simulation', 'RPG', 'release_year', 'Shared/Split Screen', 'Playable without Timed Input', 
 'Remote Play Together', 'clip_umap_3', 'clip_umap_0', 'Casual']

def transform_for_knn(df):
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

def predict_knn(model_data, test_df, train_df):
    X_test_knn = test_df[VARIABLES_GANADORAS]
    y_pred_knn = model_data.predict(X_test_knn)
    y_pred_knn = np.clip(y_pred_knn, 0, None)
    return y_pred_knn

def _get_best_knn_params(X_train, y_train):
    """
    Busca los mejores hiperparámetros para el modelo KNN utilizando Optuna.
    """
    def objective(trial):
        n_neighbors = trial.suggest_int('n_neighbors', 3, 50)
        weights = trial.suggest_categorical('weights', ['uniform', 'distance'])
        p = trial.suggest_int('p', 1, 2)

        todas_sesgadas = ['price_overview', 'num_languages', 'total_games_by_publisher', 'total_games_by_developer']
        cols_sesgadas = [c for c in VARIABLES_GANADORAS if c in todas_sesgadas and c in X_train.columns]
        cols_binarias = [c for c in VARIABLES_GANADORAS if c in X_train.columns and set(X_train[c].dropna().unique()).issubset({0, 1, 0.0, 1.0})]
        cols_normales = [c for c in VARIABLES_GANADORAS if c in X_train.columns and c not in cols_sesgadas + cols_binarias]

        preprocessor = ColumnTransformer(transformers=[
            ('sesgadas', PowerTransformer(method='yeo-johnson'), cols_sesgadas),
            ('normales', StandardScaler(), cols_normales),
            ('binarias', 'passthrough', cols_binarias)
        ], remainder='drop')

        pipeline = Pipeline([
            ('prep', preprocessor),
            ('knn', KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights, p=p, n_jobs=-1))
        ])

        final_model = TransformedTargetRegressor(
            regressor=pipeline,
            func=np.log1p,
            inverse_func=np.expm1
        )

        cv = KFold(n_splits=5, shuffle=True, random_state=seed)
        
        scores = cross_validate(
            final_model, X_train, y_train,
            cv=cv,
            scoring='neg_mean_absolute_error',
            n_jobs=-1
        )
        return -scores['test_score'].mean()

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=30)
    
    return study.best_params

def create_knn_model_popularity(minio):
    """
    Orquesta el entrenamiento del modelo KNN (solo tabular) y su subida a wandb.
    """
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Popularidad",
        name="knn-model-log",
        job_type="knn-model-log",
        config={
            "modelo": "KNN_POPULARIDAD", 
            "variables": VARIABLES_GANADORAS
        }
    )

    df_raw = read_file(popularity, minio)
    print("Aplicando transformaciones a los datos...")
    df_prepared = transform_for_knn(df_raw)
    
    X = df_prepared[VARIABLES_GANADORAS]
    y = df_prepared['recomendaciones_totales']

    bins_strat = [-1, 10, 100, 1000, 10000, float('inf')]
    y_binned = pd.cut(y, bins=bins_strat, labels=False)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y_binned
    )

    print("Buscando los mejores parámetros para el modelo KNN...")
    best_params = _get_best_knn_params(X_train, y_train)
    print("Mejores parámetros encontrados:", best_params)
    
    wandb.config.update({"params": best_params})

    todas_sesgadas = ['price_overview', 'num_languages', 'total_games_by_publisher', 'total_games_by_developer']
    cols_sesgadas = [c for c in VARIABLES_GANADORAS if c in todas_sesgadas and c in X_train.columns]
    cols_binarias = [c for c in VARIABLES_GANADORAS if c in X_train.columns and set(X_train[c].dropna().unique()).issubset({0, 1, 0.0, 1.0})]
    cols_normales = [c for c in VARIABLES_GANADORAS if c in X_train.columns and c not in cols_sesgadas + cols_binarias]

    preprocessor = ColumnTransformer(transformers=[
        ('sesgadas', PowerTransformer(method='yeo-johnson'), cols_sesgadas),
        ('normales', StandardScaler(), cols_normales),
        ('binarias', 'passthrough', cols_binarias)
    ], remainder='drop')

    final_model = TransformedTargetRegressor(
        regressor=Pipeline([
            ('prep', preprocessor),
            ('knn', KNeighborsRegressor(**best_params, n_jobs=-1))
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

    os.makedirs(models_popularidad_path(), exist_ok=True)
    write_to_file(final_model, popularidad_knn_log_file, minio)
    print(f"Modelo guardado en {popularidad_knn_log_file}")

    run.finish()


def main(minio = {"minio_write": False, "minio_read": False}):
    create_knn_model_popularity(minio)

if __name__ == "__main__":
    main()
