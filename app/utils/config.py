import pandas as pd
import numpy as np 
from sklearn.cluster import KMeans
from pathlib import Path
from joblib import load
from dotenv import load_dotenv

def project_root():
    """Devuelve un objecto Path con la raíz del proyecto"""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            current = parent
            break
    return current

# Rutas de archivos de datos
HISTORIC_GAMES_DATA_PATH = project_root() / "data/processed/historic_games_data.parquet"
POPULARITY_DATA_PATH = project_root() / "data/processed/popularidad.parquet"
PRICES_DATA_PATH = project_root() / "data/processed/precios.parquet"
PRICE_MODEL_PATH = project_root() / "models/precios/knncompleteclusters.pkl"

def load_env_file():
    """Carga el archivo .env si existe en la raíz del proyecto."""
    path_env = project_root() / ".env"
    
    if path_env.exists():
        load_dotenv(dotenv_path=path_env)
        print(f".env cargado con exito")
    else:
        print("Advertencia: No se encontró .env, se usarán variables de entorno del sistema.")

def app_dir():
    """Devuelve un objecto Path con el directorio de la aplicación (app/)"""
    return project_root() / "app"

#TODO: Implementar lectura de minio para los modelos y datos
def read_historic_games_data():
    """Lee el parquet de datos que contiene historic_games_data.parquet
    """
    print(f'Reading data from {HISTORIC_GAMES_DATA_PATH}')
    try:
        data = pd.read_parquet(HISTORIC_GAMES_DATA_PATH)
    except FileNotFoundError:
        raise FileNotFoundError("Historic games data file not found")
    print('Data read correctly')
    return data
