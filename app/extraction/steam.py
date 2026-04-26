"""Módulo de requests a las distintas APIs de Steam.
"""
import requests
import datetime
from sentence_transformers import SentenceTransformer
from PIL import Image, ImageStat
from io import BytesIO

# Url de la API de appdetails
APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
APPREVIEWSHISTOGRAM_URL = "https://store.steampowered.com/appreviewhistogram/"
APPREVIEWS_URL = "https://store.steampowered.com/appreviews/"

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

def get_appreviewshistogram(appid: str, release_date : str):
    url = APPREVIEWSHISTOGRAM_URL + appid

    params_info = {"l": "english"}
    appreviewhistogram = {}

    data = _request_url (url, params_info)

    # Caso en el que no haya ninguna review: los rollups están vacíos
    if data.get("results") is None or data["results"].get("rollups") is None:
        raise ValueError("Appreviewhistogram request with no content", appid)

    appreviewhistogram["start_date"] = _unix_to_date_string(data["results"]["start_date"])
    appreviewhistogram["end_date"] = _unix_to_date_string(data["results"]["end_date"])
    appreviewhistogram["rollup_type"] = data["results"]["rollup_type"]
    release_day = release_date.split("-")[2]

    # Buscamos que barra del histograma hay que coger
    idx = 0
    rollups = data["results"].get("rollups", [])

    if not rollups:
        raise ValueError("No rollups found", appid)
    
           
    # indice del primer rollup en el que la fecha es mayor o igual a la fecha de salida
    for i in range(len(rollups)):
        idx = i
        rollup_start_date = _unix_to_date_string(rollups[i].get("date"))
        if rollup_start_date > release_date:
            idx = max(0, idx-1)
            break
    
    hist_date = _unix_to_date_string(rollups[idx].get("date"))
    hist_day = hist_date.split("-")[2]
    days = 0
    data = {"date" : hist_date, "recommendations_up" : 0, "recommendations_down" : 0}

    if appreviewhistogram.get("rollup_type") == "week":
        for rollup in rollups[idx : idx + 4]:
            days += 7 # numero de dias en una semana
            data["recommendations_up"] += rollup.get("recommendations_up", 0)
            data["recommendations_down"] += rollup.get("recommendations_down", 0)
        days -= (int(release_day) - int(hist_day))
            
    elif appreviewhistogram.get("rollup_type") == "month":
        days = 30 - int(release_day)
        data["recommendations_up"] += rollups[idx].get("recommendations_up", 0)
        data["recommendations_down"] += rollups[idx].get("recommendations_down", 0)

        if int(release_day) > 15 and idx+1 < len(rollups):
            days = 60 - int(release_day)
            data["recommendations_up"] += rollups[idx+1].get("recommendations_up", 0)
            data["recommendations_down"] += rollups[idx+1].get("recommendations_down", 0)
        
    days = max(days, 1)
            
    appreviewhistogram["rollups"] = {
        "date": data["date"], 
        "recommendations_up": data["recommendations_up"], 
        "recommendations_down": data["recommendations_down"],
        "recommendations_up_per_day": round(data["recommendations_up"] / days, 2),
        "recommendations_down_per_day": round(data["recommendations_down"] / days, 2),
        "total_recommendations": data["recommendations_up"] + data["recommendations_down"],
        "total_recommendations_per_day": round((data["recommendations_up"] + data["recommendations_down"]) / days, 2),
        "dias":days
    }

    return appreviewhistogram

def get_reviews_text(appid : str) -> list[dict]:
    """Dado un APPID obtiene 100 reseñas de ese juego.
    """
    url = APPREVIEWS_URL + appid
    params = {
        "json": 1,
        "language": "english",
        "purchase_type": "all",
        "filter": "recent",
        "num_per_page": 100,
        "cursor": "*"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data_json = response.json()
    except Exception:
        return []

    reviews_list = []
    for rev in data_json.get("reviews", []):
        review = {
            "id_resenya":   rev["recommendationid"],
            "id_usuario":   rev["author"].get("steamid"),
            "texto":        rev["review"].strip(),
            "valoracion":   rev["voted_up"],
            "peso":         rev["weighted_vote_score"],
            "early_access": rev["written_during_early_access"],
        }
        reviews_list.append(review)

    return reviews_list

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

def _unix_to_date_string(timestamp):
    """
    Convierte un timestamp Unix a formato YYYY-MM-DD
    
    Args:
        timestamp (int): Timestamp Unix
    
    Returns:
        str: Fecha en formato YYYY-MM-DD
    """
    try:
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        return None

if __name__ == '__main__':
    pass