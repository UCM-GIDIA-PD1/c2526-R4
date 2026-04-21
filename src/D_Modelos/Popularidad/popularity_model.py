import pandas as pd
import numpy as np
from sklearn.preprocessing import KBinsDiscretizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score

from src.D_Modelos.base_model import BaseModel
from src.utils.config import seed

class PopularityModel(BaseModel):
    def __init__(self, run_name: str, model_path, minio: dict):
        super().__init__(project_name="Popularidad", run_name=run_name, model_path=model_path, minio=minio)

    def _preprocess_data(self, df, config):
        avoid_multicollinearity = config.get("avoid_multicol", True)
        df_clean = df.copy()
        
        erase_columns = ['id', 'name', 'v_resnet', 'v_convnext']
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
        
        return df_clean.fillna(0)

    def _create_stratified_bins(self, y, n_bins=5):
        bins = np.zeros(len(y), dtype=int)
        mask_pos = y > 0
        if mask_pos.sum() > n_bins:
            kb = KBinsDiscretizer(n_bins=n_bins-1, encode='ordinal', strategy='quantile', random_state=seed)
            bins[mask_pos] = kb.fit_transform(y[mask_pos].values.reshape(-1, 1)).flatten() + 1
        return bins

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
            "y_binned_train": y_binned_train  # Necesario para StratifiedKFold
        }

    def _calculate_metrics(self, y_true, y_pred) -> dict:
        return {
            "mae": mean_absolute_error(y_true, y_pred),
            "rmse": root_mean_squared_error(y_true, y_pred),
            "r2": r2_score(y_true, y_pred)
        }