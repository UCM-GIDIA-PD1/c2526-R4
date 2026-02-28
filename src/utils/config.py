import os
from pathlib import Path

"""
Se encarga de trabajar con los archivos de configuración y tiene variables con las que se trabaja en todo el proyecto
"""


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
    identif = os.environ.get("PD1_ID")
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
    current = Path(__file__).resolve()

    for parent in current.parents:
        if (parent / ".git").exists():
            current = parent
            break
    return current

def data_path():
    path = project_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path

def raw_data_path():
    path = data_path() / "raw"
    path.mkdir(parents=True, exist_ok=True)
    return path

def processed_data_path():
    path = data_path() / "processed"
    path.mkdir(parents=True, exist_ok=True)
    return path

def config_path():
    path = project_root() / "config_files"
    path.mkdir(parents=True, exist_ok=True)
    return path

def error_log_path():
    path = data_path() / "error_logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


# Variables de proyecto
members = 6
config_file = config_path() / "config.json"

# Script A
appidlist_file = raw_data_path() / "appids_list.json.gz"

# Script B
steam_log_file = error_log_path() / "steam_log_file.jsonl"
gamelist_file = raw_data_path() / "games_info.jsonl.gz"

# Script C1
youtube_scraping_file = raw_data_path() / "info_steam_youtube1.jsonl.gz"

# Script C2
yt_statslist_file =  raw_data_path() / "youtube_statistics.jsonl.gz"

# Script D
steam_reviews_top100_file = raw_data_path() / "rest_games_total_reviews.json.gz"
steam_reviews_rest_file = raw_data_path() / "top_100_games_total_reviews.json.gz"
steam_reviews_file = raw_data_path() / "steam_reviews.json.gz"

# Script E
banners_file = raw_data_path() / "info_imagenes.jsonl.gz"

# ------ SCRIPTS DE TRANSFORMACIÓN ------ #
# transformación de imágenes
P_banners_file = processed_data_path() / "P_info_imagenes.jsonl.gz"