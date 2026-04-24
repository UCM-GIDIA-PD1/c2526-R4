"""
Dado popularidad.parquet, ejecuta el modelo óptimo para predecir recomendaciones_totales
"""
import numpy as np
import pandas as pd
import optuna
import warnings

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.preprocessing import PowerTransformer, MinMaxScaler, QuantileTransformer, FunctionTransformer, StandardScaler
from sklearn.neighbors import KNeighborsRegressor
from sklearn.model_selection import StratifiedKFold, cross_validate
from umap import UMAP

from src.utils.files import read_file
from src.utils.config import popularity, popularidad_knn_log_file, seed
from src.D_Modelos.Popularidad.popularity_model import PopularityModel


warnings.filterwarnings('ignore')

VARIABLES_GANADORAS = [
    'commentCountTotal', 'Free To Play', 'Family Sharing', 'ema_reviews_publishers', 
    'Steam Trading Cards', 'Steam Cloud', 'num_languages', 'price_overview', 'Steam Achievements', 
    'Online Co-op', 'Simulation', 'RPG', 'Custom Volume Controls', 'release_year', 
    'clip_umap_0', 'Remote Play Together', 'Online PvP', 'clip_umap_2', 'Playable without Timed Input', 
    'Shared/Split Screen']

['Family Sharing', 'commentCountTotal', 'Free To Play', 'ema_reviews_publishers', 
 'Steam Trading Cards', 'Steam Cloud', 'num_languages', 'price_overview', 
 'Steam Achievements', 'Simulation', 'Online Co-op', 'RPG', 'release_year', 
 'Custom Volume Controls', 'Online PvP', 'Single-player', 'Playable without Timed Input', 
 'Shared/Split Screen', 'clip_umap_0', 'PvP']

def get_clip_matrix(X):
    return np.vstack(X.iloc[:, 0].values)

def slice_umap(X):
    return X[:, [0]]

class KNNPopularity(PopularityModel):
    def __init__(self, minio: dict):
        super().__init__(
            run_name="knn-model-log",
            model_path=popularidad_knn_log_file,
            minio=minio
        )

    def _preprocess_data(self, df_raw, config):
        """
        Limpia los datos y mantiene todas las candidatas a variables ganadoras.
        El Pipeline se encargará de descartar las que Optuna decida apagar.
        """
        df_clean = super()._preprocess_data(df_raw, config)

        vars_reales = [v for v in VARIABLES_GANADORAS if not v.startswith('clip_umap_')]

        cols_to_keep = vars_reales + ['recomendaciones_totales', 'v_clip']
        df_final = df_clean[[c for c in cols_to_keep if c in df_clean.columns]].copy()

        return df_final

    def _build_pipeline(self, hyperparameters, config, X_train):
        """Construye el pipeline filtrando solo las variables seleccionadas por Optuna."""
        # La idea es que de las 20 variables mas importantes en xgboost, solo se quede con las óptimas
        # Esto es porque knn penaliza mucho la alta dimensionalidad
        selected_vars = []
        has_feature_selection = any(k.startswith('use_') for k in hyperparameters.keys())
        
        if has_feature_selection:
            # Optuna ha runneado: filtramos las que son True
            selected_vars = [var for var in VARIABLES_GANADORAS if hyperparameters.get(f'use_{var}', False)]
            clip_vars = [v for v in selected_vars if v.startswith('clip_umap_')]
            selected_vars = [v for v in selected_vars if not v.startswith('clip_umap_')]

            use_clip = len(clip_vars) > 0
            # Si Optuna decide apagar todas las variables, forzamos a usar al menos una para que no falle
            if not selected_vars:
                selected_vars = [VARIABLES_GANADORAS[0]]
        else:
            # Fallback por si se pasan parámetros sin selección de características
            clip_vars = [v for v in VARIABLES_GANADORAS if v.startswith('clip_umap_')]
            selected_vars = [v for v in VARIABLES_GANADORAS if not v.startswith('clip_umap_')]
            use_clip = len(clip_vars) > 0

        # Separamos los parámetros puros del KNN de los booleanos de las variables
        knn_params = {k: v for k, v in hyperparameters.items() if not k.startswith('use_')}

        transformer_name = knn_params.pop('transformer', 'power')
        transformer = PowerTransformer(method='yeo-johnson') if transformer_name == 'power' else QuantileTransformer(output_distribution='normal', random_state=seed)

        # Porque solo vamos a usar la componente 0
        slice_components = FunctionTransformer(slice_umap, validate=False)

        clip_pipe = Pipeline([
            ('extractor', FunctionTransformer(get_clip_matrix, validate=False)),
            ('umap', UMAP(n_components=10, random_state=seed)),
            ('slicer', slice_components),
            ('scale', MinMaxScaler())
        ])

        cols_minmax = [c for c in selected_vars if c in self.COLS_ACOTADAS and c in X_train.columns]
        cols_sesgadas = [c for c in selected_vars if c in self.COLS_SESGADAS and c in X_train.columns]
        cols_binarias = [c for c in selected_vars if c in self.COLS_BINARIAS and c in X_train.columns]
        cols_normales = [c for c in selected_vars if c in X_train.columns and c not in cols_minmax + cols_sesgadas + cols_binarias]
        
        transformers = []

        if use_clip and 'v_clip' in X_train.columns:
            transformers.append(('clip_umap', clip_pipe, ['v_clip']))

        if cols_minmax:
            transformers.append(('minmax', MinMaxScaler(), cols_minmax))

        if cols_sesgadas:
            transformers.append(('sesgadas', transformer, cols_sesgadas))

        if cols_binarias:
            transformers.append(('binarias', 'passthrough', cols_binarias))
        
        if cols_normales:
            transformers.append(('normales', StandardScaler(), cols_normales))

        preprocessor = ColumnTransformer(
            transformers=transformers,
            remainder='drop'
        )

        pipeline = Pipeline([
            ('prep', preprocessor),
            ('knn', KNeighborsRegressor(**knn_params, n_jobs=-1))
        ])

        return TransformedTargetRegressor(regressor=pipeline, func=np.log1p, inverse_func=np.expm1)

    def _optimize_hyperparameters(self, data_splits, config):
        """Optimiza hiperparámetros y realiza Feature Selection simultánea."""
        X_train = data_splits["X_train"]
        y_train = data_splits["y_train"]
        y_binned_train = data_splits["y_binned_train"]

        def objective(trial):
            params = {
                'n_neighbors': trial.suggest_int('n_neighbors', 3, 50),
                'weights': trial.suggest_categorical('weights', ['uniform', 'distance']),
                'p': trial.suggest_int('p', 1, 2),
                'transformer': trial.suggest_categorical('transformer', ['power', 'quantile'])
            }
            
            # Optuna enciende/apaga cada variable de forma independiente
            for var in VARIABLES_GANADORAS:
                if var in X_train.columns:
                    params[f'use_{var}'] = trial.suggest_categorical(f'use_{var}', [True, False])

            model = self._build_pipeline(params, config, X_train)
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
            
            scores = cross_validate(
                model, X_train, y_train,
                cv=list(cv.split(X_train, y_binned_train)),
                scoring='neg_mean_absolute_error',
                n_jobs=-1,
                error_score='raise'
            )
            return -scores['test_score'].mean()

        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=30) 
        
        return study.best_params

def main(minio={"minio_write": False, "minio_read": False}):
    df_raw = read_file(popularity, minio)
    
    modelo_knn = KNNPopularity(minio=minio)
    modelo_knn.run_experiment(df_raw, config={"avoid_multicol": True, "use_log": True})

if __name__ == "__main__":
    main()