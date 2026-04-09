'''
Dado games_info.jsonl.gz procesa el json, lo convierte en un dataframe de pandas creando columnas nuevas y
eliminando columnas innecesarias.

Archivos necesarios:

    - publisher_dict.json
    - games_info_sample_precios.jsonl.gz
    - games_info_sample_popularidad.gz
    - game_list_file (Catálogo completo para cálculo histórico)
'''

import pandas as pd
import numpy as np
from sklearn.preprocessing import MultiLabelBinarizer
from src.utils.date import get_year
from src.utils.files import read_file, erase_file
from src.utils.minio_server import upload_to_minio
from src.utils.config import steam_games_parquet_file_popularity, steam_games_parquet_file_prices
from src.utils.config import raw_game_info_popularity, raw_game_info_prices, game_list_file

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

def _calcular_target_30_dias(df):
    '''
    Calcula la estimación de reseñas a 30 días interpolando/extrapolando
    mediante una curva logarítmica. Sobrescribe la columna original para mantener compatibilidad.
    '''
    df['dias_extraccion'] = df['appreviewhistogram'].apply(
        lambda x: x.get('rollups', {}).get('dias', np.nan) if isinstance(x, dict) and isinstance(x.get('rollups'), dict) else np.nan
    )
    
    mask = df['dias_extraccion'].notna() & df['recomendaciones_totales'].notna()
    factor = np.log1p(30) / np.log1p(df.loc[mask, 'dias_extraccion'])
    
    # Sobrescribimos la variable original en lugar de crear 'estimacion_reviews_30d'
    df.loc[mask, 'recomendaciones_totales'] = np.floor(df.loc[mask, 'recomendaciones_totales'] * factor).astype(int)
    
    df.drop(columns=['dias_extraccion'], inplace=True, errors='ignore')
    return df

def _calcular_historial_entidad(df, entidad, col_objetivo, prefijo_tipo):
    '''
    Calcula el historial de una entidad.
    Usa la Media Móvil Exponencial (EMA) para dar peso a lo reciente y 
    el máximo histórico para medir el techo de la entidad.
    Incluye One-Hot Encoding para las categorías de éxito.
    '''
    col_juegos_previos = f'juegos_previos_{entidad}'
    df[col_juegos_previos] = df.groupby(entidad).cumcount()
    
    df[f'es_primer_juego_{entidad}'] = (df[col_juegos_previos] == 0).astype(int)
    
    if col_objetivo in df.columns:
        col_temp = f'{col_objetivo}_temp'
        df[col_temp] = df[col_objetivo].fillna(0)
        
        grupo = df.groupby(entidad)[col_temp]
        
        # Media Móvil Exponencial
        df[f'ema_{prefijo_tipo}_{entidad}'] = grupo.transform(
            lambda x: x.ewm(alpha=0.5, adjust=False).mean().shift(1)
        ).fillna(0)
        
        # Máximo histórico
        df[f'max_historico_{prefijo_tipo}_{entidad}'] = grupo.transform(
            lambda x: x.expanding().max().shift(1)
        ).fillna(0)
        
        # Variable categórica de nivel de éxito (Solo para popularidad)
        if prefijo_tipo == 'reviews':
            col_ema = f'ema_{prefijo_tipo}_{entidad}'
            condiciones = [
                (df[f'es_primer_juego_{entidad}'] == 1),
                (df[col_ema] < 10),
                (df[col_ema] >= 10) & (df[col_ema] <= 100),
                (df[col_ema] >= 100) & (df[col_ema] <= 1000),
                (df[col_ema] > 1000)
            ]
            col_categoria = f'categoria_exito_{entidad}'
            df[col_categoria] = np.select(condiciones, [0, 1, 2, 3, 4], default=0)
            
            # One-Hot Encoding
            dummies = pd.get_dummies(df[col_categoria], prefix=col_categoria, dtype=int)
            df = pd.concat([df, dummies], axis=1)
            df.drop(columns=[col_categoria], inplace=True)
        
        df.drop(columns=[col_temp], inplace=True)
            
    return df

def trans_general(df):
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

def trans_prices(df, minio):
    df_prices = trans_general(df, minio)
    
    df_prices['release_date_dt'] = pd.to_datetime(df_prices['release_date'], errors='coerce')
    df_prices = df_prices.sort_values(by=['release_date_dt', 'name']).reset_index(drop=True)
    
    df_prices = _calcular_historial_entidad(df_prices, 'developers', 'price_overview', 'precio')
    df_prices = _calcular_historial_entidad(df_prices, 'publishers', 'price_overview', 'precio')
    
    columnas_basura = ['release_date', 'release_date_dt', 'publishers', 'appreviewhistogram', 'developers']
    df_prices.drop(columns=columnas_basura, inplace=True, errors='ignore')
    
    return df_prices

def trans_popularity(df, minio):
    df["recomendaciones_positivas"] = df["appreviewhistogram"].apply(
        lambda x: x.get("rollups").get("recommendations_up") if isinstance(x, dict) & 
        isinstance(x.get("rollups"), dict) else None)
    
    df["recomendaciones_negativas"] = df["appreviewhistogram"].apply(
        lambda x: x.get("rollups").get("recommendations_down") if isinstance(x, dict) & 
        isinstance(x.get("rollups"), dict) else None)
    
    df.dropna(subset=["recomendaciones_positivas","recomendaciones_negativas"], inplace=True)
    df["recomendaciones_totales"] = df["recomendaciones_positivas"] + df["recomendaciones_negativas"]

    df = trans_general(df, minio)
    df = _calcular_target_30_dias(df)
    
    df['release_date_dt'] = pd.to_datetime(df['release_date'], errors='coerce')
    df = df.sort_values(by=['release_date_dt', 'name']).reset_index(drop=True)
    
    df = _calcular_historial_entidad(df, 'developers', 'recomendaciones_totales', 'reviews')
    df = _calcular_historial_entidad(df, 'publishers', 'recomendaciones_totales', 'reviews')

    columnas_basura = [
        "release_date", "release_date_dt", "price_range", "price_overview",
        "recomendaciones_positivas", "recomendaciones_negativas", 
        'publishers', 'appreviewhistogram', 'developers'
    ]
    df.drop(columns=columnas_basura, inplace=True, errors="ignore")
    
    return df

def B_games_info_transformacion(minio):
    config = {
        raw_game_info_popularity: (trans_popularity, steam_games_parquet_file_popularity),
        raw_game_info_prices: (trans_prices, steam_games_parquet_file_prices)
    }

    for f_input, (transform_func, f_output) in config.items():
        print(f'Procesando muestra: {f_input.name}...')
        
        # Leemos el sample y guardamos la lista de ids
        sample_data = read_file(f_input, minio)
        sample_df = pd.DataFrame(sample_data)
        ids_a_guardar = sample_df['id'].unique()
        
        # Leemos el catálogo entero de juegos
        print(f'Procesando catálogo histórico completo para {f_input.name}...')
        full_data = read_file(game_list_file, minio)
        full_df = pd.DataFrame(full_data)
        
        processed_full_df = transform_func(full_df, minio)
        
        # Dejamos solo las filas del dataframe que estaban en el sample
        df_final = processed_full_df[processed_full_df['id'].isin(ids_a_guardar)].reset_index(drop=True)
        
        df_final.to_parquet(f_output)

        if minio.get("minio_write", False):
            if upload_to_minio(f_output):
                erase_file(f_output)

        
if __name__ == '__main__':
    B_games_info_transformacion()