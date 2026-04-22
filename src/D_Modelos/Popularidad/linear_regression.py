"""
Dado popularidad.parquet, ejecuta el modelo óptimo para predecir recomendaciones_totales
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
import warnings
import wandb

from sklearn.preprocessing import StandardScaler, MinMaxScaler, FunctionTransformer, QuantileTransformer
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression
from sklearn.decomposition import PCA

from src.utils.files import read_file
from src.utils.config import popularidad_linear_regression_file, popularidad_linear_regression_log_file
from src.utils.config import popularity, seed
from src.D_Modelos.Popularidad.popularity_model import PopularityModel

warnings.filterwarnings('ignore')

def get_clip_matrix(X):
    return np.vstack(X.iloc[:, 0].values)

def select_features(X, indices=None):
    return X[:, indices]

class LinearRegressionPopularity(PopularityModel):
    
    def _preprocess_data(self, df_raw, config):
        """Limpieza base asegurando que v_clip no se destruya."""
        df_clean = super()._preprocess_data(df_raw, config)

        if 'v_clip' in df_clean.columns:
            zero_vector = np.zeros(512)
            df_clean['v_clip'] = df_clean['v_clip'].apply(
                lambda x: x if isinstance(x, (list, np.ndarray)) else zero_vector
            )
            
        return df_clean

    def _get_preprocessor_and_cols(self, X_train):
        """
        Replica exactamente las transformaciones del KNN y devuelve 
        el ColumnTransformer junto con el orden exacto de las columnas de salida.
        """
        vars_reales = [v for v in X_train.columns if v != 'v_clip' and not v.startswith('clip_pca_')]

        cols_minmax = [c for c in vars_reales if c in self.COLS_ACOTADAS]
        cols_sesgadas = [c for c in vars_reales if c in self.COLS_SESGADAS]
        cols_binarias = [c for c in vars_reales if c in self.COLS_BINARIAS]
        cols_normales = [c for c in vars_reales if c not in cols_minmax + cols_sesgadas + cols_binarias]

        transformers = []
        output_cols = []

        if 'v_clip' in X_train.columns:
            clip_pipe = Pipeline([
                ('extractor', FunctionTransformer(get_clip_matrix, validate=False)),
                ('pca', PCA(n_components=10, random_state=seed)),
                ('scale', MinMaxScaler())
            ])
            transformers.append(('clip_pca', clip_pipe, ['v_clip']))
            output_cols.extend([f'clip_pca_{i}' for i in range(10)])

        if cols_minmax:
            transformers.append(('minmax', MinMaxScaler(), cols_minmax))
            output_cols.extend(cols_minmax)

        # PowerTransformer(method='yeo-johnson')
        # QuantileTransformer(output_distribution='normal', random_state=seed)
        if cols_sesgadas:
            transformers.append(('sesgadas', QuantileTransformer(output_distribution='normal', random_state=seed), cols_sesgadas))
            output_cols.extend(cols_sesgadas)

        if cols_binarias:
            transformers.append(('binarias', 'passthrough', cols_binarias))
            output_cols.extend(cols_binarias)
            
        if cols_normales:
            transformers.append(('normales', StandardScaler(), cols_normales))
            output_cols.extend(cols_normales)

        preprocessor = ColumnTransformer(transformers=transformers, remainder='drop')
        return preprocessor, output_cols

    def _optimize_hyperparameters(self, data_splits, config):
        """Optimiza variables usando Forward Selection (AIC) y evalúa el resultado con CV."""
        X_train_raw = data_splits["X_train"]
        y_train_raw = data_splits["y_train"]
        y_binned_train = data_splits["y_binned_train"]
        
        X_train = X_train_raw.copy()
        y_train = y_train_raw.copy()
        
        use_log = config.get("use_log", False)
        y_train_target = np.log1p(y_train) if use_log else y_train

        preprocessor, output_cols = self._get_preprocessor_and_cols(X_train)
        X_train_transformed = preprocessor.fit_transform(X_train)
        
        X_train_df = pd.DataFrame(X_train_transformed, columns=output_cols, index=X_train.index)

        initial_variables = list(X_train_df.columns)
        selected_variables = []
        current_score = float('inf') 
        step = 0
        
        while initial_variables:
            scores_with_candidates = []
            
            for candidate in initial_variables:
                variables = selected_variables + [candidate]
                X_train_const = sm.add_constant(X_train_df[variables], has_constant='add')
                
                model = sm.OLS(y_train_target, X_train_const).fit()
                scores_with_candidates.append((model.aic, candidate))
                
            best_new_score, best_candidate = min(scores_with_candidates) 
            
            if best_new_score < current_score:
                selected_variables.append(best_candidate)
                initial_variables.remove(best_candidate)
                current_score = best_new_score
                step += 1

                wandb.log({
                    "fs_iteration": step,
                    "fs_aic_score": current_score,
                    "fs_num_variables": len(selected_variables),
                })
            else:
                break 
                
        params = {"selected_variables": selected_variables}

        return params

    def _build_pipeline(self, hyperparameters, config, X_train):
        """Construye un pipeline nativo aplicando un filtro antes de la Regresión."""
        selected_vars = hyperparameters.get("selected_variables", [])
        
        preprocessor, output_cols = self._get_preprocessor_and_cols(X_train)
        
        if selected_vars:
            indices_ganadores = [output_cols.index(v) for v in selected_vars if v in output_cols]
            selector = FunctionTransformer(select_features, kw_args={'indices': indices_ganadores}, validate=False)
            
            pipeline = Pipeline([
                ('prep', preprocessor),
                ('selector', selector),
                ('lr', LinearRegression(n_jobs=-1))
            ])
        else:
            pipeline = Pipeline([
                ('prep', preprocessor),
                ('lr', LinearRegression(n_jobs=-1))
            ])

        if config.get("use_log", False):
            return TransformedTargetRegressor(
                regressor=pipeline,
                func=np.log1p,
                inverse_func=np.expm1
            )
            
        return pipeline

    def run_experiment(self, df_raw, config, hyperparameters=None):
        config["avoid_multicol"] = False # Ya se encarga forward_selection
        
        use_log = config.get("use_log", False)
        log_suffix = "log" if use_log else "raw"
        
        self.run_name = f"linear-regression-{log_suffix}"
        self.model_path = popularidad_linear_regression_log_file if use_log else popularidad_linear_regression_file

        return super().run_experiment(df_raw, config, hyperparameters)


def main(minio={"minio_write": False, "minio_read": False}):
    df_raw = read_file(popularity, minio)

    for log in [True, False]:
        my_config = {"use_log": log}
        
        modelo = LinearRegressionPopularity(
            run_name="", 
            model_path="",
            minio=minio
        )
        
        modelo.run_experiment(df_raw, config=my_config)

if __name__ == "__main__":
    main()