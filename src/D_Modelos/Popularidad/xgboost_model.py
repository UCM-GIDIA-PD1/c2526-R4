import numpy as np
import xgboost as xgb
import optuna
from umap import UMAP
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.preprocessing import FunctionTransformer
from sklearn.model_selection import StratifiedKFold, cross_validate

from src.utils.files import read_file
from src.utils.config import popularity, seed
from src.utils.config import popularidad_xgboost_file, popularidad_xgboost_log_file
from src.utils.config import popularidad_xgboost_nomulti_file, popularidad_xgboost_log_nomulti_file
from src.D_Modelos.Popularidad.popularity_model import PopularityModel

import warnings
warnings.filterwarnings('ignore')

def get_clip_matrix(X):
    return np.vstack(X.iloc[:, 0].values)

class XGBoostPopularity(PopularityModel):
    def _build_preprocessor(self, X_train):
        """Crea el transformador columnas para las variables del DataFrame"""
        numeric_columns = [col for col in X_train.columns if col != 'v_clip']
        
        clip_pipe = Pipeline([
            ('extractor', FunctionTransformer(get_clip_matrix, validate=False)),
            ('pca', UMAP(n_components=10, random_state=seed))
        ])
        
        return ColumnTransformer([
            ('clip_pca', clip_pipe, ['v_clip']),
            ('numeric', 'passthrough', numeric_columns)
        ], remainder='drop')

    def _build_pipeline(self, hyperparameters, config, X_train):
        use_log = config.get("use_log", True)
        params = hyperparameters.copy()
        
        if not use_log:
            params['objective'] = 'reg:tweedie'
            params.setdefault('tweedie_variance_power', 1.5)

        preprocessor = self._build_preprocessor(X_train)
        
        reg_base = Pipeline([
            ('prep', preprocessor), 
            ('xgb_reg', xgb.XGBRegressor(**params))
        ])

        if use_log:
            return TransformedTargetRegressor(regressor=reg_base, func=np.log1p, inverse_func=np.expm1)
        
        return reg_base

    def _optimize_hyperparameters(self, data_splits, config):
        X_train = data_splits["X_train"]
        y_train = data_splits["y_train"]
        y_binned_train = data_splits["y_binned_train"]
        use_log = config.get("use_log", True)

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

            model = self._build_pipeline(param, config, X_train)
            
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
            cv_results = cross_validate(
                model, X_train, y_train, 
                scoring='neg_root_mean_squared_error', 
                cv=list(cv.split(X_train, y_binned_train)), n_jobs=1
            )
            return -cv_results['test_score'].mean()

        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=30) 
        
        best_params = study.best_params
        best_params.update({'random_state': seed, 'n_jobs': -1})
        
        return best_params
    
    def run_experiment(self, df_raw, config, hyperparameters=None):
        avoid_multicol = config.get("avoid_multicol", True)
        use_log = config.get("use_log", True)

        multicol_suffix = "no_multicol" if avoid_multicol else "with_multicol"
        log_suffix = "log" if use_log else "raw"
        self.run_name = f"xgboost-{multicol_suffix}-{log_suffix}"

        if avoid_multicol:
            self.model_path = popularidad_xgboost_log_nomulti_file if use_log else popularidad_xgboost_nomulti_file
        else:
            self.model_path = popularidad_xgboost_log_file if use_log else popularidad_xgboost_file

        modelo_final = super().run_experiment(df_raw, config, hyperparameters)

        # Imprimimos importancias
        pipeline_real = modelo_final.regressor_ if use_log else modelo_final
        importancias = pipeline_real.named_steps['xgb_reg'].feature_importances_

        df_prep = self._preprocess_data(df_raw, config)
        numeric_columns = [col for col in df_prep.columns if col != 'v_clip' and col != 'recomendaciones_totales']
        nombres = [f"clip_umap_{i}" for i in range(10)] + numeric_columns

        lista_importancias = sorted(zip(nombres, importancias), key=lambda x: x[1], reverse=True)
        print("\nTop 20 variables:")
        print(lista_importancias[:20])

        return modelo_final

def main(minio={"minio_write": False, "minio_read": False}):
    df_raw = read_file(popularity, minio)
    my_config = {"avoid_multicol": True, "use_log": True}
    
    modelo = XGBoostPopularity(
        run_name="",
        model_path="",
        minio=minio
    )
    
    modelo.run_experiment(df_raw, config=my_config)

if __name__ == "__main__":
    main()