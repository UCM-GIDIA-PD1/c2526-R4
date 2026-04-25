"""Módulo de requests a las distintas APIs de Steam.
"""
import requests
import datetime
from sentence_transformers import SentenceTransformer
from PIL import Image, ImageStat
from io import BytesIO

# Url de la API de appdetails
APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"

# Modelo CLIP para las imágenes
MODEL_CLIP = SentenceTransformer('clip-ViT-B-32')


def get_appdetails(appid : str) -> dict:
    """Obtiene la información de un juego identificado por su APPID de la API de appdetails.
    """
    print(f"Obteniendo información de {appid}")
    
    # Realizamos request a la API de appdetails
    params_info = {"appids": appid, "cc": "eur"}
    data = _request_url(APPDETAILS_URL, params_info)
    if data.get(appid) is None or not data[appid].get("success", False):
        raise ValueError("Appdetails request with no content", appid)
    
    # Una vez hecho el request obtenemos la información
    appdetails = {}

    game_data = data[appid]["data"]
    free_game_po = {
                        "currency" : "EUR",
                        "initial" : 0,
                        "final" : 0,
                        "discount_percent" : 0,
                        "initial_formatted" : "0€",
                        "final_formatted" : "0€"
                    }
    appdetails["name"] = game_data.get("name")
    appdetails["required_age"] = game_data.get("required_age")
    appdetails["short_description"] = game_data.get("short_description")
    appdetails["header_url"] = game_data.get("header_image")
    appdetails["price_overview"] = game_data.get("price_overview", free_game_po)
    appdetails["supported_languages"] = _parse_supported_languages(game_data.get("supported_languages", ""))
    appdetails["capsule_img"] = game_data.get("capsule_imagev5")
    appdetails["developers"] = game_data.get("developers")
    appdetails["publishers"] = game_data.get("publishers")
    appdetails["categories"] = game_data.get("categories")
    appdetails["genres"] = game_data.get("genres")
    appdetails["metacritic"] = game_data.get("metacritic")
    release_data = game_data.get("release_date",{})
    release_date = _format_date_string(release_data.get("date",""))
    if release_data.get("coming_soon", True):
        raise ValueError("Coming soon game", appid)
    if release_date is None:
        raise ValueError(f"Failed to parse date: '{release_data.get('date','')}'", appid)
    appdetails["release_date"] = _format_date_string(release_data.get("date","")) 

    return appdetails

def get_image_metadata(url: str) -> tuple[float, list]:
    """Obtiene el embedding y el brillo a partir de la url de la imagen
    """
    print(f"Obteniendo metadatos de la imagen {url}")
    # Cargar imagen desde URL
    response = requests.get(url)
    img = Image.open(BytesIO(response.content)).convert('RGB')
    
    # Obtener brilo
    stat = ImageStat.Stat(img)
    brillo = round(stat.mean[0], 4)
    
    # Extraer embedding
    feat_clip = MODEL_CLIP.encode(img)
    vector_clip = [round(float(x), 4) for x in feat_clip.tolist()]
    
    img.close()
    
    return brillo, vector_clip

def _request_url(url : str ,params : dict) -> dict:
    """Hace un request.get de la url con los parámetros dados.
    Si el request ha sido correcto se devuelve el json de los datos.
    """
    response = requests.get(url, params=params)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if("application/json" not in content_type):
        raise ValueError("Request does not return a json")
    return response.json()

def _format_date_string(date : str) -> datetime.datetime:
    """
    Convierte fechas de Steam a formato 'YYYY-MM-DD'.
    Soporta múltiples formatos.
    """
    try:
        dt = datetime.datetime.strptime(date, "%d %b, %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None
    
def _parse_supported_languages(raw_html : str) -> list:
    """
    Parsea los idiomas del campo supported_languages de la API de Steam.
    Devuelve una lista de idiomas.
    """
    if not raw_html:
        return []
    raw_languages = raw_html.split("<br>")[0]
    processed_languages = raw_languages.replace("<strong>*</strong>","")
    language_list = [language.strip() for language in processed_languages.split(",")]
    return language_list
