import os

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
