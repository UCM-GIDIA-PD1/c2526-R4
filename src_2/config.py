import os
from pathlib import Path
import platform
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
    """Devuelve un objecto Path con el directorio de config."""
    path = project_root() / "config_files"
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

# ------- Configuración de TOR --------
TOR_CONTROL_PORT = 9051
TORRC_PATH = config_files_folder() / "torrc"
TOR_SOCKS_PROXY = "socks5://127.0.0.1:9050"
BROWSER_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

# ------- Configuración de para ChromiumPage --------
_sys = platform.system()
if _sys == 'Windows':
    USER_AGENTS = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36']
elif _sys == 'Darwin':
    USER_AGENTS = ['Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36']
else:
    USER_AGENTS = ['Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36']

COMMON_RESOLUTIONS = [(1920, 1080), (1366, 768), (1536, 864), (1440, 900)]