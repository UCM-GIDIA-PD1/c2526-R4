import pandas as pd

# Importaciones utilizadas por ficheros auxiliares
from src.utils.files import read_file
from src.utils.config import load_env_file, project_root

def app_dir():
    """Devuelve un objecto Path con el directorio de la aplicación (app/)"""
    return project_root() / "app"

# Rutas de archivos de datos
HISTORIC_GAMES_DATA_PATH = project_root() / "data/processed/historic_games_data.parquet"
POPULARITY_DATA_PATH = project_root() / "data/processed/popularidad.parquet"
PRICES_DATA_PATH = project_root() / "data/processed/precios.parquet"
GAME_FETCH_DATA_PATH = app_dir() / "data/games_info_fetch.parquet"
PRICE_MODEL_PATH = project_root() / "models/precios/knncompleteclusters.pkl"

#TODO: Implementar lectura de minio para los modelos y datos
def read_historic_games_data():
    """Lee el parquet de datos que contiene historic_games_data.parquet"""
    print(f'Reading data from {HISTORIC_GAMES_DATA_PATH}')
    try:
        data = pd.read_parquet(HISTORIC_GAMES_DATA_PATH)
    except FileNotFoundError:
        raise FileNotFoundError("Historic games data file not found")
    print('Data read correctly')
    return data
