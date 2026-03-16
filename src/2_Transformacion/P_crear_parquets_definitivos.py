"""
Dados los ficheros limpios de información, los ficheros de información de imágenes y los ficheros de youtube
junta los dataframes creando los 3 dataframes finales que utilizaremos: uno para cada problema. 
"""

import pandas as pd
from src.utils.files import read_file, erase_file
from src.utils.minio_server import upload_to_minio
from src.utils.config import banners_file_popularity, banners_file_prices, steam_games_parquet_file_popularity 
from src.utils.config import steam_games_parquet_file_prices, prices, popularity, yt_stats_parquet_file
"""
    Crea el parquet del problema de los precios 
    """
def create_prices_parquet(minio):
    """
    Crea el parquet del problema de los precios, juntando los parquets resultantes de B y E de transformación.
    
    Return:
        None
    """
    df_B = pd.DataFrame(read_file(steam_games_parquet_file_prices, minio))
    df_E = pd.DataFrame(read_file(banners_file_prices, minio))

    df_E["id"] = df_E["id"].astype(str)

    df = pd.merge(df_B, df_E, on="id")

    df.dropna()
    df.to_parquet(prices)

    if minio["minio_write"]:
        if upload_to_minio(prices):
            erase_file(prices)

def create_popularity_parquet(minio):
    """
    Crea el parquet del problema de la popularidad, juntando los parquets de B, C, E de transformación 
    
    Return:
        None
    """
    df_B = pd.DataFrame(read_file(steam_games_parquet_file_popularity, minio))
    df_E = pd.DataFrame(read_file(banners_file_popularity, minio))
    df_C = pd.DataFrame(read_file(yt_stats_parquet_file, minio))

    df_E["id"] = df_E["id"].astype(str)
    df_C["id"] = df_C["id"].astype(str)

    df = pd.merge(df_B, df_E, on = "id")
    df = pd.merge(df, df_C, on = "id")

    df.dropna()
    df.to_parquet(popularity)

    if minio["minio_write"]:
        if upload_to_minio(popularity):
            erase_file(popularity)

def crear_parquets(minio):
    create_popularity_parquet(minio)
    create_prices_parquet(minio)

if __name__ == '__main__':
    crear_parquets()