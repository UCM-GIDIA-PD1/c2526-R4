import os
import requests
from tqdm import tqdm
from utils.files import write_to_file
from utils.date import format_date_string, unix_to_date_string
from utils.exceptions import AppdetailsException, ReviewhistogramException, SteamAPIException

def log_appid_errors(appid, reason, log_filepath):
    data = {appid : reason}
    write_to_file(data, log_filepath)

def _parse_supported_languages(raw_html):
    if not raw_html:
        return []
    
    raw_languages = raw_html.split("<br>")[0]
    processed_languages = raw_languages.replace("<strong>*</strong>","")
    language_list = [language.strip() for language in processed_languages.split(",")]
    return language_list

def _request_url(session, params_info, url):
    """
    Realiza una petición GET a una URL específica utilizando una sesión.

    Args:
        sesion (requests.Session): Sesión de la librería requests para 
            'reciclar' la conexión.
        params_info (dict): Diccionario con los parámetros de consulta.
        url (str): Dirección URL del endpoint de la API.

    Returns:
        dict | None: Datos decodificados del JSON si la petición es exitosa. 
        Retorna None si ocurre un error de conexión o un estado HTTP erróneo.
    """
    try:
        response = session.get(url, params=params_info)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if("application/json" not in content_type):
            raise SteamAPIException("Request does not return a json")

        return response.json()
    except requests.exceptions.HTTPError as e:
        raise SteamAPIException(f"HTTP error: {e}")
    
    except requests.exceptions.RequestException as e:
        raise SteamAPIException(f"Request error: {e}")
    
    except ValueError as e:
        raise SteamAPIException(f"Json decodification error: {e}")

# Por defecto extrae todos los appids, desde el principio hasta el final. n_appids es mucho más que los juegos que hay en steam
# La función se encarga de parar si no hay más datos
def get_appids(n_appids=1000000, last_appid = 0):
    """
    Función que guarda en appid_list.json.gz una lista de appids (str). Ejemplo: ["10", "20", "30"]
    Requiere una api key de steam guardada en la una variable de entorno llamada 'STEAM_API_KEY'
    
    params:
        n_appids (int): número de appids que se quiere extraer
        last_appid (string): appid por el que se quiere comenzar a extraer, no se incluye
    
    returns:
        appid_list (list): Devuelve la lista de los APPIDs
    """

    # url e info
    url = "https://api.steampowered.com/IStoreService/GetAppList/v1/"

    # Cogemos la API
    API_KEY = os.environ.get("STEAM_API_KEY")
    if API_KEY is None:
        raise SteamAPIException("Enviroment variable STEAM_API_KEY not found")

    max_results = min(n_appids, 50000) # Cuantos resultados se quiere por request
    info = {"key": API_KEY, "max_results" : max_results, "last_appid": last_appid}

    # Creamos el json que va a tener todos los datos
    appid_list = []

    # Creamos la sesión
    session = requests.Session()
    
    # Bucle que itera sobre los elementos restantes de la lista de APPID de Steam
    print("Starting extraction...")

    with tqdm(total=n_appids, desc="appids extracted: ", unit="appids") as pbar:
        while n_appids > 0:
            # Si existe data lo guardamos en el diccionario content
            data = _request_url(session, info, url)
            
            if not data:
                break
            
            appid_list.extend([str(app["appid"]) for app in data["response"].get("apps",[])])
            
            # Decrementamos el número de APPIDs restantes
            appids_extraidos = len(data["response"].get("apps",[]))
            pbar.update(appids_extraidos)
            n_appids -= appids_extraidos
            info["max_results"] = min(n_appids, 50000)

            # Si no hay más juegos salir del bucle y dar proceso por completado
            if not data["response"].get("have_more_results"):
                pbar.total = pbar.n
                pbar.refresh()
                print(f"No more results. Number of appids extracted {len(appid_list)}")
                break
            
            # Modificamos el last_appid con el último de la petición anterior
            info["last_appid"] = data["response"].get("last_appid")    

    return appid_list

def get_appdetails(appid, sesion):
    """
    Extrae y limpia los detalles técnicos y comerciales de un juego desde la API de Steam.

    Args:
        appid (str): ID de la aplicación (AppID) en Steam.
        sesion (requests.Session): Sesión persistente para realizar la petición HTTP.

    Returns:
        dict: Diccionario con la información procesada (nombre, precio, idiomas, etc.).
        Retorna un diccionario vacío si la petición falla o el ID no es válido.
    """

    # Creamos la url
    url = "https://store.steampowered.com/api/appdetails"

    # Hacemos el request a la página y creamos el json que va a almacenar la info
    params_info = {"appids": appid, "cc": "eur"}
    appdetails = {}
    
    # La función solicitud_url trata las distintas excepciones posibles
    data = _request_url(sesion, params_info, url)

    if data.get(appid) is None or not data[appid].get("success", False):
        raise AppdetailsException("Appdeatils request with no content", appid)

    game_data = data[appid]["data"]

    free_game_po = {
                        "currency" : "EUR",
                        "initial" : 0,
                        "final" : 0,
                        "discount_percent" : 0,
                        "initial_formatted" : "0€",
                        "final_formatted" : "0€"
                        }
    
    # Metemos la información útil
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
        raise AppdetailsException("Game filtered, coming soon")
    if release_date is None:
        raise AppdetailsException(f"Failed to parse date: '{release_data.get('date','')}'", appid)
    
    appdetails["release_date"] = format_date_string(release_data.get("date","")) 
    
    return appdetails


def get_appreviewhistogram(appid, session, release_date):
    """
    Obtiene y procesa estadísticas de reseñas de un juego en Steam. Extrae métricas
    generales y calcula el agregado de recomendaciones (positivas y negativas)
    correspondientes aproximadamente al primer mes de vida del juego.

    Args:
        appid (str): El ID del juego en Steam (APPID).
        sesion (requests.Session): Sesión ya abierta de requests.
        release_date (str): Formato YYYY-MM-DD

    Returns:
        dict: Diccionario con las fechas de inicio/fin y los datos agregados de 'rollups'.
        Retorna un diccionario vacío si no hay datos disponibles.
    """
    
    # Creamos la url
    url = "https://store.steampowered.com/appreviewhistogram/" + appid
    
    # Hacemos el request a la página y creamos el json que va a almacenar la info
    params_info = {"l": "english"}
    appreviewhistogram = {}
    
    # La función solicitud_url trata las distintas excepciones posibles
    data = _request_url(session, params_info, url)

    # Caso en el que no haya ninguna review: los rollups están vacíos
    if data.get("results") is None or data["results"].get("rollups") is None:
        raise ReviewhistogramException("Appreviewhistogram request with no content", appid)
        

    appreviewhistogram["start_date"] = unix_to_date_string(data["results"]["start_date"])
    appreviewhistogram["end_date"] = unix_to_date_string(data["results"]["end_date"])
    appreviewhistogram["rollup_type"] = data["results"]["rollup_type"]

    release_day = release_date.split("-")[2]
    # Buscamos que barra del histograma hay que coger
    idx = 0
    rollups = data["results"].get("rollups", [])

    if not rollups:
        raise ReviewhistogramException("No rollups found", appid)
        
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
        days -= (release_day - hist_day)
            
    elif appreviewhistogram.get("rollup_type") == "month":
        days = 30 - int(release_day), 1
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

if __name__ == "__main__":
    pass