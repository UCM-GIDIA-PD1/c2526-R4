"""Módulo de transformación de datos para el problema de popularidad.

Realiza las transformaciones necesarias para tener los mismos datos que necesita el modelo para predecir.
"""

import pandas as pd
import numpy as np
from transformation.common import  initial_transformations, add_img_info

GENRES = ['Action', 'Adventure', 'Casual', 'Early Access', 'Free To Play',
'Indie', 'RPG', 'Simulation', 'Strategy']

CATEGORIES = ['Co-op', 'Custom Volume Controls', 'Family Sharing',
'Full controller support', 'Multi-player', 'Online Co-op',
'Online PvP', 'Partial Controller Support',
'Playable without Timed Input', 'PvP', 'Remote Play Together',
'Shared/Split Screen', 'Single-player', 'Steam Achievements',
'Steam Cloud', 'Steam Leaderboards', 'Steam Trading Cards']

HISTORY_COLS = [
    'num_juegos_previos_developers', 'es_primer_juego_developers',
    'ema_reviews_developers', 'max_historico_reviews_developers',
    'num_juegos_previos_publishers', 'es_primer_juego_publishers',
    'ema_reviews_publishers', 'max_historico_reviews_publishers',
]

def _transform_game_dict(game: dict, appid: str, historic_data: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma un diccionario con información de un juego Steam
    en una única fila de DataFrame lista para usar con el modelo.
    """
    row = {}
    row = initial_transformations(game, row)

    # Géneros
    genres_list = [g['description'] for g in game.get('genres', []) if isinstance(g, dict)]
    for genre in GENRES:
        row[genre] = 1 if genre in genres_list else 0

    # Categorías
    categories_list = [c['description'] for c in game.get('categories', []) if isinstance(c, dict)]
    for cat in CATEGORIES:
        row[cat] = 1 if cat in categories_list else 0

    # Datos históricos de Developers y Publishers
    match = historic_data[historic_data['id'].astype(str) == str(appid)]
    print(match)
    if not match.empty:
        hist_row = match.iloc[0]
        for col in HISTORY_COLS:
            row[col] = hist_row[col]
    else:
        for col in HISTORY_COLS:
            row[col] = 0

    return pd.DataFrame([row])

def _transform_reviews(row : pd.DataFrame, appreviewshistogram : dict) -> pd.DataFrame:
    """Dada una fila de dataFrame se le añade el campo de número de reviews totales.
    """
    rollups = appreviewshistogram.get("rollups") if isinstance(appreviewshistogram, dict) else None

    if isinstance(rollups, dict):
        rec_up   = rollups.get("recommendations_up",   0) or 0
        rec_down = rollups.get("recommendations_down", 0) or 0
        row["recomendaciones_totales"] = rec_up + rec_down
    else:
        row["recomendaciones_totales"] = None

    return row

def _transform_yt_data(row: pd.DataFrame, yt_data: dict) -> pd.DataFrame:
    """
    Dada una fila de dataFrame obtiene todas las columnas de la información de YouTube.
    Añade las métricas por vídeo (viewCount, likeCount, commentCount) y yt_score.
    """
    YT_STAT_COLS = [
        f"video_{i}_video_statistics.{stat}"
        for i in range(4)
        for stat in ["viewCount", "likeCount", "commentCount", "favoriteCount"]
    ]

    for col in YT_STAT_COLS:
        row[col] = 0
    row["yt_score"] = 0

    if not isinstance(yt_data, dict):
        return row

    video_statistics = yt_data.get("video_statistics", [])
    if not isinstance(video_statistics, list):
        return row

    score_total = 0
    encontrado_alguna_metrica = False

    for i, video in enumerate(video_statistics[:4]):
        if not isinstance(video, dict):
            continue

        stats = video.get("video_statistics", {}) or {}

        for stat in ["viewCount", "likeCount", "commentCount", "favoriteCount"]:
            val = pd.to_numeric(stats.get(stat, 0), errors="coerce")
            row[f"video_{i}_video_statistics.{stat}"] = int(np.nan_to_num(val))

        v = row[f"video_{i}_video_statistics.viewCount"]
        l = row[f"video_{i}_video_statistics.likeCount"]
        c = row[f"video_{i}_video_statistics.commentCount"]

        if v > 0 or l > 0 or c > 0:
            encontrado_alguna_metrica = True
            score_total += (
                0.5 * np.log10(v + 1) +
                0.3 * np.log10(l + 1) +
                0.2 * np.log10(c + 1)
            )

    row["yt_score"] = score_total if encontrado_alguna_metrica else 0
    return row

def transform_for_popularity(game: dict,
                            appid: str, 
                            historic_data: pd.DataFrame, 
                            v_clip: list, 
                            brillo: float, 
                            appreviewshistogram : dict,
                            yt_data : dict) -> pd.DataFrame:
    """Realiza las transformaciones necesarias para tener una fila apta para el modelo de predicción de popularidad
    
    Columnas resultantes:
    Index(['description_len', 'price_overview', 'num_languages',
       'release_year', 'Action', 'Adventure', 'Casual', 'Early Access',
       'Free To Play', 'Indie', 'RPG', 'Simulation', 'Strategy', 'Co-op',
       'Custom Volume Controls', 'Family Sharing', 'Full controller support',
       'Multi-player', 'Online Co-op', 'Online PvP',
       'Partial Controller Support', 'Playable without Timed Input', 'PvP',
       'Remote Play Together', 'Shared/Split Screen', 'Single-player',
       'Steam Achievements', 'Steam Cloud', 'Steam Leaderboards',
       'Steam Trading Cards', 'num_juegos_previos_developers',
       'es_primer_juego_developers', 'ema_reviews_developers',
       'max_historico_reviews_developers', 'num_juegos_previos_publishers',
       'es_primer_juego_publishers', 'ema_reviews_publishers',
       'max_historico_reviews_publishers', 'v_clip', 'brillo',
       'recomendaciones_totales', 'video_0_video_statistics.viewCount',
       'video_0_video_statistics.likeCount',
       'video_0_video_statistics.commentCount',
       'video_0_video_statistics.favoriteCount',
       'video_1_video_statistics.viewCount',
       'video_1_video_statistics.likeCount',
       'video_1_video_statistics.commentCount',
       'video_1_video_statistics.favoriteCount',
       'video_2_video_statistics.viewCount',
       'video_2_video_statistics.likeCount',
       'video_2_video_statistics.commentCount',
       'video_2_video_statistics.favoriteCount',
       'video_3_video_statistics.viewCount',
       'video_3_video_statistics.likeCount',
       'video_3_video_statistics.commentCount',
       'video_3_video_statistics.favoriteCount', 'yt_score'],
      dtype='str')
    """
    
    row = _transform_game_dict(game, appid, historic_data)
    row = add_img_info(row, v_clip, brillo)
    row = _transform_reviews(row, appreviewshistogram)
    row = _transform_yt_data(row, yt_data)
    row.drop(columns=['price_range'], inplace=True)
    return row

