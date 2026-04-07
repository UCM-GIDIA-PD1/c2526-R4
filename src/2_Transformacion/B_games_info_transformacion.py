'''
Dado games_info.jsonl.gz procesa el json, lo convierte en un dataframe de pandas creando columnas nuevas y
eliminando columnas innecesarias.

Archivos necesarios:

    - publisher_dict.json
    - games_info_sample_precios.jsonl.gz
    - games_info_sample_popularidad.gz
'''

import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer
from src.utils.date import get_year
from src.utils.files import read_file, erase_file
from src.utils.minio_server import upload_to_minio
from src.utils.config import steam_games_parquet_file_popularity, steam_games_parquet_file_prices
from src.utils.config import raw_game_info_popularity, raw_game_info_prices, steam_publishers_count, steam_developers_count

def _get_name(x):
    '''
    Dado un diccionario devuelve el valor del campo name.

    Args:
        x (dict): Diccionario de appdetails.
    
    Returns:
        str: String del valor del campo 'name' del diccionario.
    '''
    if isinstance(x,dict):
        return x.get("name")
    else:
        return None

def _get_genres(x):
    '''
    Dado un diccionario itera por el campo 'genres' que contiene a su vez una lista de diccionarios, cada uno con 
    los campos 'id' y 'description', para obtener una lista de géneros.

    Args:
        x (dict): Diccionario de appdetails.
    
    Returns:
        list: Lista de strings de géneros de un juego
    '''
    if not isinstance(x, dict):
        return []
    genres = x.get('genres', [])
    if not isinstance(genres, list):
        return []
    return [g.get('description') for g in genres if isinstance(g, dict)]

def _get_categories(x):
    '''
    Dado un diccionario itera por el campo 'categories' que contiene a su vez una lista de diccionarios, cada uno con 
    los campos 'id' y 'description', para obtener una lista de categorías.

    Args:
        x (dict): Diccionario de appdetails.
    
    Returns:
        list: Lista de strings de categorías de un juego
    '''
    if not isinstance(x,dict):
        return []
    categories = x.get("categories", [])
    if not isinstance(categories, list):
        return []
    return [c.get("description") for c in categories if isinstance(c, dict)]

def price_range(x):
    '''
    Dado el precio de un juego devuelve el rango de precio en el que se encuentra.

    Args:
        x (float): Precio de un juego
    
    Returns:
        str: String que representa el rango de precio.
    '''
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

def _number_publishers(x, publishers_dict):
    strX = str(x)
    nGames = publishers_dict.get(strX)
    return nGames if nGames else 0

def _get_info_reviews(author):
    
    return None

def _get_info_prices(author):
    return None

def trans_general(df, minio):
    df = df.join(df["appdetails"].apply(pd.Series))

    df["categories"] = df["appdetails"].apply(lambda x: _get_categories(x))
    df["genres"] = df["appdetails"].apply(lambda x: _get_genres(x))
    df["description_len"] = df["short_description"].apply(lambda x : len(x))
    df["name"] = df["appdetails"].apply(lambda x : _get_name(x))
    df['price_overview'] = df['price_overview'].apply(lambda x: x.get('initial')/100)
    df['price_range'] = df['price_overview'].apply(lambda x: price_range(x))
    df['publishers'] = df['publishers'].apply(lambda x: x[0] if x else None) # Nos quedamos con la primera
    df['developers'] = df['developers'].apply(lambda x: x[0] if x else None) # Nos quedamos con la primera
    df['num_languages'] = df['supported_languages'].apply(lambda x: len(x))
    df["release_year"] = df ["release_date"].apply(lambda x: get_year(x))

    publishers_dict = dict(read_file(steam_publishers_count, minio))
    df['total_games_by_publisher'] = df['publishers'].apply(lambda x: _number_publishers(x,publishers_dict))

    developers_dict = dict(read_file(steam_developers_count, minio))
    df['total_games_by_developer'] = df['developers'].apply(lambda x: _number_publishers(x,developers_dict))
    

    df = categories_and_genres(df) # Aplicamos a categorías y géneros one hot encoding

    # Eliminamos columnas sin usar
    df.drop(columns=["appdetails", 'appreviewhistogram', 'header_url', 'capsule_img', 'metacritic', "publishers", "developers", 
                    'required_age', "short_description", "release_date", "supported_languages", "genres", "categories"]
                    , inplace=True,errors="ignore")
    
    return df

def categories_and_genres(df):
    mlb_genres = MultiLabelBinarizer()

    df_genres = pd.DataFrame(
        mlb_genres.fit_transform(df['genres']),
        columns=mlb_genres.classes_,
        index=df.index
    )

    threshold_genres = len(df_genres) * 0.05
    cols_to_keep_genres = df_genres.columns[df_genres.sum() >= threshold_genres]
    df_genres = df_genres[cols_to_keep_genres]

    mlb_categories = MultiLabelBinarizer()

    df_categories = pd.DataFrame(
        mlb_categories.fit_transform(df['categories']),
        columns=mlb_categories.classes_,
        index=df.index
    )

    threshold_categories = len(df_categories) * 0.05
    cols_to_keep_categories = df_categories.columns[df_categories.sum() >= threshold_categories]
    df_categories = df_categories[cols_to_keep_categories]

    df_final = pd.concat([df, df_genres], axis=1)
    df_final = pd.concat([df_final, df_categories], axis=1)

    return df_final


def trans_prices(df, minio):
    df_prices = trans_general(df, minio)
    df_prices[['mode_price_by_publisher', 'average_price_by_publisher']] = df_prices.apply(_get_info_prices('publisher'),
                                                                                  axis=1, result_type='expand')
    df_prices[['mode_price_by_developer', 'average_price_by_developer']] = df_prices.apply(_get_info_prices('developer'),
                                                                                  axis=1, result_type='expand')
    return df_prices

def trans_popularity(df, minio):
    df["recomendaciones_positivas"] = df["appreviewhistogram"].apply(
        lambda x: x.get("rollups").get("recommendations_up_per_day") if isinstance(x, dict) & 
        isinstance(x.get("rollups"), dict) else None)
    
    df["recomendaciones_negativas"] = df["appreviewhistogram"].apply(
        lambda x: x.get("rollups").get("recommendations_down_per_day") if isinstance(x, dict) & 
        isinstance(x.get("rollups"), dict) else None)
    
    # Eliminamos nulos
    df.dropna(subset=["recomendaciones_positivas","recomendaciones_negativas"],inplace = True)
    df["recomendaciones_totales"] = df["recomendaciones_positivas"] + df["recomendaciones_negativas"]

    df = trans_general(df, minio)

    df[['total_reviews_by_publisher', 'average_reviews_by_publisher']] = df.apply(_get_info_reviews('publisher'),
                                                                                  axis=1, result_type='expand')
    df[['total_reviews_by_developer', 'average_reviews_by_developer']] = df.apply(_get_info_reviews('developer'),
                                                                                  axis=1, result_type='expand')
    
    df.drop(columns=["prince_range", "recomendaciones_positivas", "recomendaciones_negativas"], inplace=True,errors="ignore")
    return df

def B_games_info_transformacion(minio):
    config = {
        raw_game_info_popularity: (trans_popularity, steam_games_parquet_file_popularity),
        raw_game_info_prices: (trans_prices, steam_games_parquet_file_prices)
    }

    for f_input, (transform_func, f_output) in config.items():
        print(f'Procesando {f_input.name}...')
        
        data = read_file(f_input, minio)
        df = transform_func(pd.DataFrame(data), minio)
        df.to_parquet(f_output)

        if minio["minio_write"]:
            if upload_to_minio(f_output):
                erase_file(f_output)

        
if __name__ == '__main__':
    B_games_info_transformacion()