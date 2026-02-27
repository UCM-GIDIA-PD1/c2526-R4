'''
Dado games_info.jsonl.gz procesa el json, lo convierte en un dataframe 
de pandas creando columnas nuevas y eliminando columnas innecesarias.
'''

import pandas as pd
from src.utils.config import raw_data_path, processed_data_path
from src.utils.files import read_file

def _get_name(x):
    '''
    Función usada para procesar nombres dentro de appdetails,
    devuelve la string que contiene el campo 'name'
    '''
    if isinstance(x,dict):
        return x.get("name")
    else:
        return None

def _get_genres(x):
    '''
    Procesa el diccionario de géneros de appdetails de un juego,
    devuelve una lista de géneros (string)
    '''
    if not isinstance(x, dict):
        return []
    genres = x.get('genres', [])
    if not isinstance(genres, list):
        return []
    return [g.get('description') for g in genres if isinstance(g, dict)]

def _get_categories(x):
    '''
    Procesa el diccionario de categorías de appdetails de un juego,
    devuelve una lista de categorías (string)
    '''
    if not isinstance(x,dict):
        return []
    categories = x.get("categories", [])
    if not isinstance(categories, list):
        return []
    return [c.get("description") for c in categories if isinstance(c, dict)]

def _is_free(x):
    '''
    Procesa el diccionario de precio de appdetails de un juego,
    devuelve un int con el precio inicial del juego
    '''
    if not isinstance(x,dict):
        return []
    price_ov = x.get("price_overview", [])
    if not isinstance(price_ov, dict):
        return []
    return price_ov.get("initial") == 0

def price_range(x):
    '''
    Dado un precio lo categoriza en rangos: Gratis, (0,5), [5,10), [10,15),
    [15,20), [20,30), [40,inf)
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
        return'[30.00,39.99]'
    elif x >= 40:
        return '>40'


if __name__ == '__main__':

    print('Obteniendo archivo')
    games_info_path = raw_data_path() / 'games_info.jsonl.gz'
    games_info = read_file(games_info_path)
    assert games_info, 'No se ha podido leer el archivo'

    print('Tranformando a dataframe')
    # Creamos el dataframe base
    df = pd.DataFrame(games_info)
    df = df.join(df["appdetails"].apply(pd.Series))

    # Procesamos appdetails para crear una columna por cada campo
    df["name"] = df["appdetails"].apply(lambda x : _get_name(x))
    df["free"] = df["appdetails"].apply(lambda x: _is_free(x))
    df["categories"] = df["appdetails"].apply(lambda x: _get_categories(x))
    df["genres"] = df["appdetails"].apply(lambda x: _get_genres(x))
    df['price_overview'] = df['price_overview'].apply(lambda x: x.get('initial')/100)
    df['price_range'] = df['price_overview'].apply(lambda x: price_range(x))
    df["recomendaciones_positivas"] = df["appreviewhistogram"].apply(lambda x: x.get("rollups").get("recommendations_up") if isinstance(x, dict) & isinstance(x.get("rollups"), dict) else None)
    df["recomendaciones_negativas"] = df["appreviewhistogram"].apply(lambda x: x.get("rollups").get("recommendations_down") if isinstance(x, dict) & isinstance(x.get("rollups"), dict) else None)
    
    df['publishers'] = df['publishers'].apply(lambda x: x[0] if x else None) # Nos quedamos con la primera
    df['developers'] = df['developers'].apply(lambda x: x[0] if x else None) # Nos quedamos con la primera
    df['required_age'] = df['required_age'].apply(lambda x: int(x))
 
    # Dropeamos nulos y columnas sin usar
    df.dropna(subset=["recomendaciones_positivas","recomendaciones_negativas"],inplace = True)
    df["recomendaciones_totales"] = df["recomendaciones_positivas"] + df["recomendaciones_negativas"]

    df.drop(columns=["appdetails", 'appreviewhistogram', 'header_url', 'capsule_img', 'metacritic'], inplace=True,errors="ignore")
    

    print('Almacenando')
    # Almacenamos en parquet y csv
    df.to_parquet(processed_data_path() / "games_info.parquet")
    # df.to_csv('data/games_info.csv', index=False)