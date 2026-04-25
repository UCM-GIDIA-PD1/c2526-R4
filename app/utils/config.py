import pandas as pd
import numpy as np 
from sklearn.cluster import KMeans
from pathlib import Path
from joblib import load
from dotenv import load_dotenv


def load_env_file():
    """Carga el archivo .env si existe en la raíz del proyecto."""
    path_env = project_root() / ".env"
    
    if path_env.exists():
        load_dotenv(dotenv_path=path_env)
        print(f".env cargado con exito")
    else:
        print("Advertencia: No se encontró .env, se usarán variables de entorno del sistema.")


def project_root():
    """Devuelve un objecto Path con la raíz del proyecto"""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            current = parent
            break
    return current

def app_dir():
    """Devuelve un objecto Path con el directorio de la aplicación (app/)"""
    return project_root() / "app"

# Rutas de archivos de datos
HISTORIC_GAMES_DATA_PATH = project_root() / "data/processed/historic_games_data.parquet"
POPULARITY_DATA_PATH = project_root() / "data/processed/popularidad.parquet"
PRICES_DATA_PATH = project_root() / "data/processed/precios.parquet"
PRICE_MODEL_PATH = project_root() / "models/precios/knncompleteclusters.pkl"

#TODO: Implementar lectura de minio para los modelos y datos

def read_popularity():
    """Obtiene el dataFrame de popularidad.parquet"""
    print(f'Reading popularity data from {POPULARITY_DATA_PATH}')
    try:
        data = pd.read_parquet(POPULARITY_DATA_PATH)
    except FileNotFoundError:
        raise FileNotFoundError("Popularity file not found")

    print('Data read correctly')
    return data
    
def read_prices():
    """Obtiene el dataFrame de precios.parquet"""
    print(f'Reading price data from {PRICES_DATA_PATH}')
    try:
        data = pd.read_parquet(PRICES_DATA_PATH)
    except FileNotFoundError:
        raise FileNotFoundError("Price file not found")

    print('Data read correctly')

    matrix = np.stack(data['v_clip'].values)
    kmeans = KMeans(n_clusters=8, random_state=42)
    data['cluster'] = kmeans.fit_predict(matrix)
    data = data.drop(columns=['v_clip'])

    return data

def read_historic_games_data():
    print(f'Reading data from {HISTORIC_GAMES_DATA_PATH}')
    try:
        data = pd.read_parquet(HISTORIC_GAMES_DATA_PATH)
    except FileNotFoundError:
        raise FileNotFoundError("Historic games data file not found")
    print('Data read correctly')
    return data

def find_row(appid, df):
    """Dado un appid de un juego, obtiene la fila correspendiente a ese juego en 
    el dataFrame"""
    row = df.loc[df['id'] == appid]
    print(row)
    return row

def prices_transform(data):
    """Transformación básica para el modelo de precios"""
    data = data.drop(columns= ['id','name','price_overview','v_resnet','v_convnext'])
    data['release_year'] = data['release_year'].apply(lambda x : int(x))
    return data
