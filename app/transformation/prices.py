"""Módulo de transformación de datos para el problema de precios
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
    'ema_precio_developers', 'max_historico_precio_developers',
    'num_juegos_previos_publishers', 'es_primer_juego_publishers',
    'ema_precio_publishers', 'max_historico_precio_publishers',
]

def _transform_game_dict(game: dict, appid : str, historic_data : pd.DataFrame) -> pd.DataFrame:
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


def transform_for_prices(game : dict, appid : str, historic_data : pd.DataFrame, v_clip : list, brillo : float):
    row = _transform_game_dict(game, appid, historic_data)
    row = add_img_info(row ,v_clip, brillo)

    return row


if __name__ == '__main__': 
    pass