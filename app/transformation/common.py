"""Módulo de transformación para la información de los juegos común entre precios y popularidad.
"""

import pandas as pd
from src.B_Transformacion.B_games_info_transformacion import price_range

def initial_transformations(game: dict, row : dict) -> pd.DataFrame: 
    """Dado un juego (dict) extrae los campos: 

        - description_len
        - price_overview
        - price_range
        - num_languages
        - release_year
    """
    # Descripción
    row['description_len'] = len(game.get('short_description', ''))

    # Precio
    price_dict = game.get('price_overview', {})
    price = price_dict.get('initial', 0) / 100 if isinstance(price_dict, dict) else 0
    row['price_overview'] = price
    row['price_range'] = price_range(price)

    # Idiomas
    row['num_languages'] = len(game.get('supported_languages', []))

    # Fecha
    try:
        row['release_year'] = pd.to_datetime(game.get('release_date')).year
    except Exception:
        row['release_year'] = 0

    return row

def add_img_info(row : pd.DataFrame, v_clip : list, brillo : float) -> pd.DataFrame:
    """Añade a un dataframe los embeddins y el brillo de una imagen
    """
    row['v_clip'] = [v_clip]
    row['brillo'] = brillo

    return row

if __name__ == '__name__':
    pass
