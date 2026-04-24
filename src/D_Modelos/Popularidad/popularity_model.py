import os
import wandb
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, median_absolute_error

from src.utils.config import seed
from src.utils.files import read_file, write_to_file

class PopularityModel(ABC):
    COLS_SESGADAS = ['price_overview', 'total_games_by_publisher', 'total_games_by_developer',
                    'num_juegos_previos_developers', 'es_primer_juego_developers', 
                    'ema_reviews_developers', 'max_historico_reviews_developers',
                    'num_juegos_previos_publishers', 'es_primer_juego_publishers',
                    'ema_reviews_publishers', 'max_historico_reviews_publishers',
                    'video_0_video_statistics.viewCount',
                    'video_0_video_statistics.likeCount',
                    'video_0_video_statistics.favoriteCount',
                    'video_0_video_statistics.commentCount',
                    'video_1_video_statistics.viewCount',
                    'video_1_video_statistics.likeCount',
                    'video_1_video_statistics.favoriteCount',
                    'video_1_video_statistics.commentCount',
                    'video_2_video_statistics.viewCount',
                    'video_2_video_statistics.likeCount',
                    'video_2_video_statistics.favoriteCount',
                    'video_2_video_statistics.commentCount',
                    'video_3_video_statistics.viewCount',
                    'video_3_video_statistics.likeCount',
                    'video_3_video_statistics.favoriteCount',
                    'video_3_video_statistics.commentCount',
                    'viewCountTotal', 'likeCountTotal', 'commentCountTotal']
    COLS_ACOTADAS = ['description_len', 'num_languages', 'brillo', 'release_year']
    COLS_BINARIAS = ['Action', 'Adventure', 'Casual', 'Early Access', 'Free To Play', 'Indie', 'RPG',
       'Simulation', 'Strategy', 'Co-op', 'Custom Volume Controls',
       'Family Sharing', 'Full controller support', 'Multi-player',
       'Online Co-op', 'Online PvP', 'Partial Controller Support',
       'Playable without Timed Input', 'PvP', 'Remote Play Together',
       'Shared/Split Screen', 'Single-player', 'Steam Achievements',
       'Steam Cloud', 'Steam Leaderboards', 'Steam Trading Cards', 
       'es_primer_juego_developers', 'es_primer_juego_publishers']

    def __init__(self, run_name: str, model_path, minio: dict):
        self.project_name = "Popularidad"
        self.run_name = run_name
        self.model_path = model_path
        self.minio = minio
        self.entity = "pd1-c2526-team4"

    @abstractmethod
    def _optimize_hyperparameters(self, data_splits, config):
        pass

    @abstractmethod
    def _build_pipeline(self, hyperparameters, config, X_train):
        pass

    @staticmethod
    def _format_metrics(metrics: dict) -> str:
        return " | ".join(f"{k.upper()}: {v:.4f}" for k, v in metrics.items())
    
    def _predict(self, model, X_test, X_train=None):
        preds = model.predict(X_test)
        return np.maximum(preds, 0)

    def run_experiment(self, df_raw, config, hyperparameters=None):
        """Flujo de ejecución de un modelo"""
        
        run = wandb.init(
            entity=self.entity, 
            project=self.project_name, 
            name=self.run_name,
            job_type="model-training",
            config=config
        )
        print(f"\nIniciando experimento: {self.run_name} ---")

        df_prep = self._preprocess_data(df_raw, config)
        data_splits = self._split_data(df_prep)
        
        X_train, X_test = data_splits["X_train"], data_splits["X_test"]
        y_train, y_test = data_splits["y_train"], data_splits["y_test"]

        # Intentamos cargar hiperparámetros en caso de que ya se hayan encontrado los óptimos
        model_data = None
        try:
            model_data = read_file(self.model_path, self.minio)
        except FileNotFoundError:
            pass
        
        if model_data is not None:
            print(f"Cargando modelo existente de {self.model_path}...")
            modelo_final = model_data["model"]
            best_params = model_data.get("hyperparameters", {})
        else:
            print("No se encontró pkl. Iniciando entrenamiento...")
            if hyperparameters:
                best_params = hyperparameters.copy()
            else:
                best_params = self._optimize_hyperparameters(data_splits, config)

            modelo_final = self._build_pipeline(best_params, config, X_train)
            modelo_final.fit(X_train, y_train)

            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            write_to_file({"model": modelo_final, "hyperparameters": best_params}, self.model_path, self.minio)
            print(f"Modelo guardado exitosamente en {self.model_path}")

        wandb.config.update({"params": best_params})
        
        preds = self._predict(modelo_final, X_test, X_train)
        metrics = self._calculate_metrics(y_test, preds)

        print(f"Resultados de {self.run_name}: {self._format_metrics(metrics)}")        
        wandb.log({f"test_{k}": v for k, v in metrics.items()}) # Logueamos estandarizado
        
        run.finish()
        return modelo_final

    # Evaluación para Z_evaluaciones.py
    def evaluate(self, df_raw, config) -> dict:
        """Hace todo el pipeline de datos y predice cargando los hiperparámetros óptimos"""
        df_prep = self._preprocess_data(df_raw, config)
        data_splits = self._split_data(df_prep)
        
        model_data = read_file(self.model_path, self.minio)
        if model_data is None:
            raise FileNotFoundError(f"No se encontró el modelo en {self.model_path} para evaluación.")
            
        modelo_final = model_data["model"]
        preds = self._predict(modelo_final, data_splits["X_test"], data_splits["X_train"])
        
        return self._calculate_metrics(data_splits["y_test"], preds)

    def _preprocess_data(self, df, config):
        avoid_multicollinearity = config.get("avoid_multicol", True)
        df_clean = df.copy()
        
        erase_columns = ['id', 'name', 'v_resnet', 'v_convnext', 'yt_score']
        df_clean = df_clean.dropna(subset=["num_juegos_previos_developers", "num_juegos_previos_publishers"], how="all")

        cols_devs = ["num_juegos_previos_developers", "es_primer_juego_developers", "ema_reviews_developers", "max_historico_reviews_developers"]
        cols_pubs = ["num_juegos_previos_publishers", "es_primer_juego_publishers", "ema_reviews_publishers", "max_historico_reviews_publishers"]

        filtro_devs = df_clean["num_juegos_previos_developers"].isna()
        filtro_pubs = df_clean["num_juegos_previos_publishers"].isna()

        df_clean.loc[filtro_devs, cols_devs] = df_clean.loc[filtro_devs, cols_pubs].values
        df_clean.loc[filtro_pubs, cols_pubs] = df_clean.loc[filtro_pubs, cols_devs].values
        
        if avoid_multicollinearity:
            df_clean["commentCountTotal"] = df_clean.filter(like="video_statistics.commentCount").sum(axis=1)
            erase_columns.extend(cols_devs + ['num_juegos_previos_publishers', 'es_primer_juego_publishers', 'max_historico_reviews_publishers'])
            erase_columns.extend(df_clean.filter(like="video_statistics").columns)
        
        df_clean = df_clean.drop(columns=[col for col in erase_columns if col in df_clean.columns])

        obj_cols = df_clean.select_dtypes(include=['object']).columns
        for col in obj_cols:
            if col != 'v_clip':
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        
        cols_to_fill = [c for c in df_clean.columns if c != 'v_clip']
        df_clean[cols_to_fill] = df_clean[cols_to_fill].fillna(0)

        return df_clean

    def _create_stratified_bins(self, y, n_bins=5):
        """
        Crea exactamente 5 bins estratificados. 
        Si hay empates masivos, los desempata al 
        azar para que todos los grupos tengan el mismo tamaño.
        """
        # Cortes basados en los datos:
        # 0 - 6 (Percentil 0-50)
        # 6 - 23 (Percentil 50-75)
        # 23 - 106 (Percentil 75-90)
        # 106 - 320 (Percentil 90-95)
        # 320+ (Top 5%)
        
        bins = pd.cut(
            y, 
            bins=[-np.inf, 6, 23, 106, 320, np.inf], 
            labels=False
        )
        return bins.values

    def _split_data(self, df_prep):
        X = df_prep.drop(columns=["recomendaciones_totales"])
        y = df_prep["recomendaciones_totales"]
        
        y_binned = self._create_stratified_bins(y, n_bins=5)
        X_train, X_test, y_train, y_test, y_binned_train, _ = train_test_split(
            X, y, y_binned, test_size=0.2, stratify=y_binned, random_state=seed
        )
        
        return {
            "X_train": X_train, 
            "X_test": X_test,
            "y_train": y_train, 
            "y_test": y_test,
            "y_binned_train": y_binned_train
        }

    def _calculate_metrics(self, y_true, y_pred) -> dict:
        return {
            "mae": mean_absolute_error(y_true, y_pred),
            "rmse": root_mean_squared_error(y_true, y_pred),
            "medae": median_absolute_error(y_true, y_pred)
        }