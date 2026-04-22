import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, median_absolute_error

from src.D_Modelos.base_model import BaseModel
from src.utils.config import seed

[
       
       'num_juegos_previos_developers', 'es_primer_juego_developers',
       'ema_reviews_developers', 'max_historico_reviews_developers',
       'num_juegos_previos_publishers', 'es_primer_juego_publishers',
       'ema_reviews_publishers', 'max_historico_reviews_publishers', 'brillo',
       'v_clip',
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
       'video_3_video_statistics.commentCount', 'yt_score', 'viewCountTotal',
       'likeCountTotal', 'commentCountTotal']

class PopularityModel(BaseModel):
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
        super().__init__(project_name="Popularidad", run_name=run_name, model_path=model_path, minio=minio)

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