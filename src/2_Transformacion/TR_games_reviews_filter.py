"""
Dado el archivo games_info.jsonl.gz, procesa el json convirtiéndolo en dataframe
y extrae los 20000 juegos con mayor número de total_recommendation. Posteriormente
se divide en 2, un dataframe con los 100 juegos con más reviews y otro con el resto
de juegos (19900).
"""

import pandas as pd
from src.utils.config import steam_reviews_top100_file, steam_reviews_rest_file, gamelist_file
from src.utils.files import read_file

def _get_total_reviews(x):
    """
    Función que extrae el número de reviews obtenidas de 
    la columna appreviewhistogram.
    
    Args:
        x (dict): diccionario que contiene la información de appreviewhistogram del juego
        
    Returns:
        int: número de recomendaciones obtenido de la columna appreviewhistogram de cadaa juego
    """
    if not isinstance(x,dict):
        return []
    if x.get("rollups"):
        return x.get("rollups").get("total_recommendations")
def _get_name(x):
    """
    Función que extrae el nombre del juego.
    
    Args:
        x (dict): diccionario perteneciente a la columna appdetails
    
    Returns:
        str: nombre del juego
    """
    if isinstance(x,dict):
        return x.get("name")
    else:
        return None


if __name__ == "__main__":
    
    print('Obteniendo archivo')
    data = read_file(gamelist_file)
    assert data, 'No se ha podido leer el archivo'
    
    print('Tranformando a dataframe')
    # Se crea el dataframe base
    df = pd.DataFrame(data)
    
    # Se obtienen las columnas necesarias
    df["name"] = df["appdetails"].apply(lambda x : _get_name(x))
    df["total_reviews"] = df["appreviewhistogram"].apply(lambda x : _get_total_reviews(x))

    # El dataframe se queda con las columnas name y total_reviews
    df = df[["id", "name", "total_reviews"]]
    # Se crea un dataframe ordenado por total_reviews
    df_sorted = df.sort_values(by="total_reviews", ascending= False)

    df_sorted.reset_index(inplace=True)

    # Dataframe correspondiente a los 100 juegos con mayor número de reviews
    df_top_100_sorted = df_sorted.head(n=100)

    # Dataframe con los juegos restantes
    df_rest_sorted = df_sorted.iloc[100:20000]

    
    print('Almacenando')
    # Almacenar los dataframes en las rutas indicadas
    df_top_100_sorted.to_json(steam_reviews_top100_file, orient= "records", compression= "gzip")
    df_rest_sorted.to_json(steam_reviews_rest_file, orient= "records", compression= "gzip")
    