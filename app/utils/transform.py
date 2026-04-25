"""Módulo de transformación de datos obtenidos de las APIs
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import MultiLabelBinarizer
from datetime import datetime

def general_transformation(df):
    df["name"] = df["appdetails"].apply(lambda x : _get_name(x))
    df["categories"] = df["appdetails"].apply(lambda x: _get_categories(x))
    df["genres"] = df["appdetails"].apply(lambda x: _get_genres(x))
    df["short_description"] = df["appdetails"].apply(lambda x: x.get("short_description", "") if isinstance(x, dict) else "")
    df["description_len"] = df["short_description"].apply(lambda x : len(x))
    
    df['price_overview_dict'] = df['appdetails'].apply(lambda x: x.get('price_overview', {}) if isinstance(x, dict) else {})
    df['price_overview'] = df['price_overview_dict'].apply(lambda x: x.get('initial', 0)/100 if isinstance(x, dict) else 0)
    df['price_range'] = df['price_overview'].apply(lambda x: price_range(x))
    
    df['supported_languages'] = df['appdetails'].apply(lambda x: x.get("supported_languages", []) if isinstance(x, dict) else [])
    df['num_languages'] = df['supported_languages'].apply(lambda x: len(x))
    
    df['publishers_list'] = df['appdetails'].apply(lambda x: x.get("publishers", []) if isinstance(x, dict) else [])
    df['publishers'] = df['publishers_list'].apply(lambda x: x[0] if x and len(x)>0 else None)
    
    df['developers_list'] = df['appdetails'].apply(lambda x: x.get("developers", []) if isinstance(x, dict) else [])
    df['developers'] = df['developers_list'].apply(lambda x: x[0] if x and len(x)>0 else None)
    
    df['release_date'] = df['appdetails'].apply(lambda x: x.get("release_date") if isinstance(x, dict) else None)
    df["release_year"] = df["release_date"].apply(lambda x: get_year(x))

    df = categories_and_genres(df)

    columnas_basura = [
        "appdetails", 'header_url', 'capsule_img', 'metacritic', 'required_age', 
        "short_description", "supported_languages", "genres", "categories",
        "price_overview_dict", "publishers_list", "developers_list"
    ]
    df.drop(columns=columnas_basura, inplace=True, errors="ignore")
    
    return df

def categories_and_genres(df):
    mlb_genres = MultiLabelBinarizer()
    df_genres = pd.DataFrame(mlb_genres.fit_transform(df['genres']), columns=mlb_genres.classes_, index=df.index)
    
    threshold_genres = len(df_genres) * 0.05
    cols_to_keep_genres = df_genres.columns[df_genres.sum() >= threshold_genres]
    df_genres = df_genres[cols_to_keep_genres]

    mlb_categories = MultiLabelBinarizer()
    df_categories = pd.DataFrame(mlb_categories.fit_transform(df['categories']), columns=mlb_categories.classes_, index=df.index)

    threshold_categories = len(df_categories) * 0.05
    cols_to_keep_categories = df_categories.columns[df_categories.sum() >= threshold_categories]
    df_categories = df_categories[cols_to_keep_categories]

    df_final = pd.concat([df, df_genres], axis=1)
    df_final = pd.concat([df_final, df_categories], axis=1)

    return df_final

def get_year(date_str):
    """
    Convierte fechas de Steam a formato 'YYYY-MM-DD'.
    Soporta múltiples formatos.

    Args:
        fecha_str (str): Fecha en formato 'DD Mon, YYYY'.

    Returns:
        str | None: La fecha en formato RFC 3339 ('YYYY-MM-DD')
        Retorna None si la fecha no se carga correctamente.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y")

    except ValueError:
        return None

def _get_name(x):
    '''Dado un diccionario devuelve el valor del campo name.'''
    if isinstance(x,dict):
        return x.get("name")
    else:
        return None

def _get_genres(x):
    '''Obtiene una lista de géneros desde el diccionario.'''
    if not isinstance(x, dict):
        return []
    genres = x.get('genres', [])
    if not isinstance(genres, list):
        return []
    return [g.get('description') for g in genres if isinstance(g, dict)]

def _get_categories(x):
    '''Obtiene una lista de categorías desde el diccionario.'''
    if not isinstance(x,dict):
        return []
    categories = x.get("categories", [])
    if not isinstance(categories, list):
        return []
    return [c.get("description") for c in categories if isinstance(c, dict)]

def price_range(x):
    '''Dado el precio devuelve el rango en string.'''
    if x == 0:
        return 'Free'
    elif x > 0 and x < 5:
        return '[0.01,4.99]'
    elif x >= 5 and x < 10:
        return '[5.00,9.99]'
    elif x >= 10 and x < 15:
        return '[10.00,14.99]'
    elif x >= 15 and x < 20:
        return '[15.00,19.99]'
    elif x >= 20 and x < 30:
        return '[20.00,29.99]'
    elif x >= 30 and x < 40:
        return '[30.00,39.99]'
    elif x >= 40:
        return '>40'




