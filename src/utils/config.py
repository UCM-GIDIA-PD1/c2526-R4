"""
Se encarga de trabajar con los archivos de configuración y tiene variables con las que se trabaja en todo el proyecto
"""

from os import environ
from pathlib import Path
from dotenv import load_dotenv

def get_appid_range(length):
    """Lee el inicio y fin de una sesión de scrapping desde un archivo de texto
    Los indices que se guardan corresponden a los de una lista, no corresponden con un appid concreto
    Si no existe el archivo se asigna la parte correspondiente a identif

    Args:
        ruta_txt: ruta del fichero de texto. Debe contener los datos en formato: 'index_inicial,index_final'
        identif: Parte de los datos que se va a extraer
        longitud: Numero de elementos del archivo
    
    Returns:
        Tupla de enteros con los valores de inicio y fin
    """
    identif = environ.get("PD1_ID")
    # procesar todos los appids
    if identif is None:
        return 0, 0, length-1
    
    assert identif.isdigit(), f"Error: El identificador no es un entero válido (valor actual: {identif})."
    int_identif = int(identif)
    assert 1 <= int_identif <= members, f"El identificador debe estar entre 1 y 6 (valor actual: {identif})."

    bloque = length // members
    start_idx = (int_identif - 1) * bloque

    if int_identif == members:
        end_idx = length - 1
    else:
        end_idx = (int_identif * bloque) - 1

    return start_idx, start_idx, end_idx

# Paths
def project_root():
    """Devuelve un objecto Path con la raíz del proyecto.

    Returns:
        Path: raíz del proyecto.
    """
    current = Path(__file__).resolve()

    for parent in current.parents:
        if (parent / ".git").exists():
            current = parent
            break
    return current

def data_path():
    """Devuelve un objecto Path con el directorio de la carpeta data.

    Returns:
        Path: directorio data del proyecto.
    """
    path = project_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path

def raw_data_path():
    """Devuelve un objecto Path con el directorio raw dentro de data.

    Returns:
        Path: directorio raw.
    """
    path = data_path() / "raw"
    path.mkdir(parents=True, exist_ok=True)
    return path

def processed_data_path():
    """Devuelve un objecto Path con el directorio processed.

    Returns:
        Path: directorio processed.
    """
    path = data_path() / "processed"
    path.mkdir(parents=True, exist_ok=True)
    return path

def config_path():
    """Devuelve un objecto Path con el directorio de config.

    Returns:
        Path: directorio config.
    """
    path = project_root() / "config_files"
    path.mkdir(parents=True, exist_ok=True)
    return path

def error_log_path():
    """Devuelve un objecto Path con el directorio de error_log.

    Returns:
        Path: directorio del archivo de log de errores.
    """
    path = data_path() / "error_logs"
    path.mkdir(parents=True, exist_ok=True)
    return path

def load_env_file():
    """Carga el archivo .env si existe en la raíz del proyecto."""
    path_env = project_root() / ".env"
    
    if path_env.exists():
        load_dotenv(dotenv_path=path_env)
        print(f".env cargado con exito")
    else:
        print("Advertencia: No se encontró .env, se usarán variables de entorno del sistema.")

# ------ VARIABLES DEL PROYECTO ------ #

# Total de miembros del equipo de extracción para dividirla en bloques
members = 6

# Config Path
config_file = config_path() / "config.json"

# ------ SCRIPTS DE EXTRACCIÓN ------ #

# Script A
appidlist_file = raw_data_path() / "appids_list.json.gz"

# Script B
steam_log_file = error_log_path() / "steam_log_file.jsonl"
gamelist_file = raw_data_path() / f"games_info.jsonl.gz"
raw_game_info_popularity = raw_data_path() / f"games_info_sample_popularidad.jsonl.gz"
raw_game_info_prices = raw_data_path() / f"games_info_sample_precios.jsonl.gz"

# Script C1
youtube_scraping_file = raw_data_path() / "info_steam_youtube1.jsonl.gz"

# Script C2
yt_statslist_file =  raw_data_path() / "youtube_statistics.jsonl.gz"

# Script D
steam_reviews_file = raw_data_path() / "steam_reviews.jsonl.gz"

# Script E
banners_file = raw_data_path() / "info_imagenes.jsonl.gz"
banners_file_popularity = raw_data_path() / "info_imagenes_popularidad.jsonl.gz"
banners_file_prices = raw_data_path() / "info_imagenes_precios.jsonl.gz"

# ------ SCRIPTS DE TRANSFORMACIÓN ------ #

# Script B
steam_games_parquet_file = processed_data_path() / "games_info.parquet"
steam_games_parquet_file_popularity = processed_data_path() / "games_info_popularity.parquet"
steam_games_parquet_file_prices = processed_data_path() / "games_info_prices.parquet"
steam_publishers_count = raw_data_path() / "publisher_dict.json"
steam_developers_count = raw_data_path() / "developer_dict.json"

# Script C
yt_stats_parquet_file = processed_data_path() / "yt_stats.parquet"

# Script D1
steam_reviews_top100_file = raw_data_path() / "rest_games_total_reviews.json.gz"
steam_reviews_rest_file = raw_data_path() / "top_100_games_total_reviews.json.gz"

# Script D2
steam_reviews_parquet_file = processed_data_path() / "steam_reviews_processed.parquet"

# Script E
P_banners_file = processed_data_path() / "P_info_imagenes.parquet"

# Scripts P
popularity = processed_data_path() / "popularidad.parquet"
prices = processed_data_path() / "precios.parquet"
reviews =  processed_data_path() / "resenyas.parquet"

# Reducción en modelo de precios
reduced_prices = processed_data_path() / "precios_reducido.parquet"