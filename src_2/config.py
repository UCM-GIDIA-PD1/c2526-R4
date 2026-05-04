import os
from pathlib import Path
import platform
from dotenv import load_dotenv

load_dotenv()
# ------- Estructura de carpetas -------
def project_root():
    """Devuelve un objecto Path con la raíz del proyecto."""
    current = Path(__file__).resolve()

    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            current = parent
            break
    return current

def config_files_folder():
    """Devuelve un objeto Path con el directorio de config."""
    path = project_root() / "config_files"
    path.mkdir(parents=True, exist_ok=True)
    return path

def data_folder():
    """Devuelve un objeto Path con el directorio de la carpeta data."""
    path = project_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path

def raw_data_folder():
    """Devuelve un objeto Path con el directorio de la carpeta data."""
    path = data_folder() / "raw"
    path.mkdir(parents=True, exist_ok=True)
    return path

def images_folder():
    """Devuelve un objeto Path con el directorio de la carpeta images."""
    path = raw_data_folder() / "images"
    path.mkdir(parents=True, exist_ok=True)
    return path

def processed_data_path():
    """Devuelve un objecto Path con el directorio processed."""
    path = data_folder() / "processed"
    path.mkdir(parents=True, exist_ok=True)
    return path

def models_folder():
    """Devuelve un objeto Path con el directorio de la carpeta models."""
    path = project_root() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path

def models_popularidad_folder():
    """Devuelve un objecto Path con el directorio models/popularidad."""
    path = models_folder() / "popularidad"
    path.mkdir(parents=True, exist_ok=True)
    return path

def models_precios_folder():
    """Devuelve un objecto Path con el directorio models/precios."""
    path = models_folder() / "precios"
    path.mkdir(parents=True, exist_ok=True)
    return path

def models_reviews_path():
    """Devuelve un objecto Path con el directorio models/reviews."""
    path = models_folder() / "reviews"
    path.mkdir(parents=True, exist_ok=True)
    return path

# ------- Variables de entorno -------
def get_env_var(name):
    """Obtiene una variable de entorno y valida su existencia."""
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"ERROR: La variable de entorno '{name}' no está configurada.")
    return value

def get_steam_api_key():
    """Obtiene la clave de API de Steam desde las variables de entorno."""
    return get_env_var("STEAM_API_KEY")

def get_youtube_api_key():
    """Obtiene la clave de API de YouTube desde las variables de entorno."""
    return get_env_var("API_KEY_YT")

def get_minio_access_key():
    """Obtiene la clave de acceso de Minio desde las variables de entorno."""
    return get_env_var("MINIO_ACCESS_KEY")

def get_minio_secret_key():
    """Obtiene la clave secreta de Minio desde las variables de entorno."""
    return get_env_var("MINIO_SECRET_KEY")

def get_extraction_id():
    """Obtiene el identificador de extracción de YouTube desde las variables de entorno."""
    return get_env_var("PD1_ID")

# ------- Configuración de TOR --------
TOR_CONTROL_PORT = 9051
TORRC_PATH = config_files_folder() / "torrc"
TOR_SOCKS_PROXY = "socks5://127.0.0.1:9050"
BROWSER_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

# ------- Configuración de para ChromiumPage --------
_sys = platform.system()
if _sys == "Windows":
    USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"]
elif _sys == "Darwin":
    USER_AGENTS = ["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"]
else:
    USER_AGENTS = ["Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"]

COMMON_RESOLUTIONS = [(1920, 1080), (1366, 768), (1536, 864), (1440, 900)]

# ------- Rutas de ficheros --------
# Steam
full_appid_list_path = raw_data_folder() / "appid_list_full.json.gz"
sample_appid_list_path = raw_data_folder() / "appid_list_sample.json.gz"

steam_details_path = raw_data_folder() / "steam_details.jsonl.gz"   # tiene appdetails y review_stats (appreviewhistogram)
steam_reviews_path = raw_data_folder() / "steam_reviews.jsonl.gz"
steam_images_path = raw_data_folder() / "steam_images.jsonl.gz"

# YouTube
youtube_video_ids_path = raw_data_folder() / "youtube_video_ids.jsonl.gz"
youtube_stats_path = raw_data_folder() / "youtube_stats.jsonl.gz"

TOTAL_MEMBERS = 6
if __name__ == "__main__":
    print(full_appid_list_path.relative_to(project_root()))