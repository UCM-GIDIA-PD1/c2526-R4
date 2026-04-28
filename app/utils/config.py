import pandas as pd

# Importaciones utilizadas por ficheros auxiliares
from src.utils.files import read_file
from src.utils.config import load_env_file, project_root
from src.utils.minio_server import download_from_minio

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

def read_games_fetch_data():
    """Lee el parquet con la información básica de los juegos (id, name, img, total_reviews) desde MinIO."""

    local_path = GAME_FETCH_DATA_PATH
    print(f'Reading games fetch data from {local_path}')

    local_path.parent.mkdir(parents=True, exist_ok=True)
    downloaded = download_from_minio(local_path, filename="app/data/games_info_fetch.parquet")

    if not downloaded:
        print("Descarga de MinIO fallida, intentando leer fichero local")

    data = read_file(local_path)
    if data is None:
        raise FileNotFoundError("Games fetch data file not found")
    print(f'Games fetch data read correctly ({len(data)} games)')
    return data
