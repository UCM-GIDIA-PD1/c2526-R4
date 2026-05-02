"""Módulo de requests a las distintas APIs de Steam.
"""
import requests
from sentence_transformers import SentenceTransformer
from PIL import Image, ImageStat
from io import BytesIO
import base64

from src.utils.date import format_date_string, unix_to_date_string
from src.A_Extraccion.utils_extraccion.steam_requests import _parse_supported_languages

# Url de la API de appdetails
APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
APPREVIEWSHISTOGRAM_URL = "https://store.steampowered.com/appreviewhistogram/"
APPREVIEWS_URL = "https://store.steampowered.com/appreviews/"

# Modelo CLIP para las imágenes
MODEL_CLIP = SentenceTransformer('clip-ViT-B-32', device='cpu')


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
    release_date = format_date_string(release_data.get("date",""))
    if release_data.get("coming_soon", True):
        raise ValueError("Coming soon game", appid)
    if release_date is None:
        raise ValueError(f"Failed to parse date: '{release_data.get('date','')}'", appid)
    appdetails["release_date"] = format_date_string(release_data.get("date","")) 

    return appdetails

def get_image_metadata(url: str) -> tuple[float, list]:
    """Obtiene el embedding y el brillo a partir de la url de la imagen (o base64)
    """
    print(f"Obteniendo metadatos de la imagen (longitud: {len(url)})")
    
    # Cargar imagen
    if url.startswith("http"):
        # Descarga desde URL
        response = requests.get(url)
        img = Image.open(BytesIO(response.content)).convert('RGB')
    elif "," in url:
        # Decodificación desde Base64 (típico de req.image)
        try:
            header, encoded = url.split(",", 1)
            data = base64.b64decode(encoded)
            img = Image.open(BytesIO(data)).convert('RGB')
        except Exception as e:
            print(f"Error decodificando base64: {e}")
            # Fallback a imagen gris si falla
            img = Image.new('RGB', (224, 224), color='gray')
    else:
        # Carga desde ruta local
        try:
            img = Image.open(url).convert('RGB')
        except Exception as e:
            print(f"Error cargando imagen local {url}: {e}")
            img = Image.new('RGB', (224, 224), color='gray')
    
    # Obtener brillo
    stat = ImageStat.Stat(img)
    brillo = round(stat.mean[0], 4)
    
    # Extraer embedding CLIP
    feat_clip = MODEL_CLIP.encode(img)
    vector_clip = [round(float(x), 4) for x in feat_clip.tolist()]
    
    img.close()
    
    return brillo, vector_clip

def get_appreviewshistogram(appid: str, release_date : str) -> dict:
    url = APPREVIEWSHISTOGRAM_URL + appid

    params_info = {"l": "english"}
    appreviewhistogram = {}

    data = _request_url (url, params_info)

    # Caso en el que no haya ninguna review: los rollups están vacíos
    if data.get("results") is None or data["results"].get("rollups") is None:
        raise ValueError("Appreviewhistogram request with no content", appid)

    appreviewhistogram["start_date"] = unix_to_date_string(data["results"]["start_date"])
    appreviewhistogram["end_date"] = unix_to_date_string(data["results"]["end_date"])
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
        rollup_start_date = unix_to_date_string(rollups[i].get("date"))
        if rollup_start_date > release_date:
            idx = max(0, idx-1)
            break
    
    hist_date = unix_to_date_string(rollups[idx].get("date"))
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
def get_reviews_text(appid: str) -> list[dict]:
    """Dado un APPID obtiene 2  00 reseñas de ese juego mediante paginación.
    """
    NUM_REVIEWS = 200
    url = APPREVIEWS_URL + appid
    params = {
        "json": 1,
        "language": "english",
        "purchase_type": "all",
        "filter": "recent",
        "num_per_page": 100,
        "cursor": "*"
    }

    reviews_list = []
    while len(reviews_list) < NUM_REVIEWS:
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data_json = response.json()
        except Exception:
            break
        new_reviews = data_json.get("reviews", [])
        if not new_reviews:
            break
        for rev in new_reviews:
            if len(reviews_list) >= NUM_REVIEWS:
                break
            reviews_list.append({
                "id_resenya":   rev["recommendationid"],
                "id_usuario":   rev["author"].get("steamid"),
                "texto":        rev["review"].strip(),
                "valoracion":   rev["voted_up"],
                "peso":         rev["weighted_vote_score"],
                "early_access": rev["written_during_early_access"],
            })
        next_cursor = data_json.get("cursor")
        if not next_cursor or next_cursor == params["cursor"]:
            break
        params["cursor"] = next_cursor
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


if __name__ == '__main__':
    pass