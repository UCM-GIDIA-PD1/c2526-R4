import os
import requests
from tqdm import tqdm
from config import data_path, error_log_path
from files import write_to_file
from date import format_date_string, unix_to_date_string
from datetime import datetime
from calendar import monthrange

def _log_appid_errors(appid, reason, log_filepath):
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
            print("The request does not return a json")
            return None
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None
    except ValueError as e:
        print(f"Json decodification error: {e}")
        return None
 
def get_appids(n_appids=1000000, last_appid = 0):
    """
    Función que guarda en appid_list.json.gz una lista de appids (str). Ejemplo: ["10", "20", "30"]
    Requiere una api key de steam guardada en la una variable de entorno llamada 'STEAM_API_KEY'
    
    :param n_appids: número de appids que se quiere extraer
    :param last_appid: appid por el que se quiere comenzar a extraer, no se incluye
    """
    # fichero destino
    filepath = data_path() / "appid_list.json.gz"

    # url e info
    url = "https://api.steampowered.com/IStoreService/GetAppList/v1/"

    # Cogemos la API
    API_KEY = os.environ.get("STEAM_API_KEY")
    assert API_KEY, "Enviroment variable STEAM_API_KEY not found"

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
                print("Request did not return data")
                return 
            
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

    write_to_file(appid_list, filepath)

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
    # archivo en el que guardamos appid que han dado error
    log_filepath = error_log_path() / "log_appdetails_error.jsonl"

    # Creamos la url
    url = "https://store.steampowered.com/api/appdetails"

    # Hacemos el request a la página y creamos el json que va a almacenar la info
    params_info = {"appids": appid, "cc": "eur"}
    appdetails = {}
    
    # La función solicitud_url trata las distintas excepciones posibles
    data = _request_url(sesion, params_info, url)

    if not data.get(appid, "") or not data[appid].get("success", False):
        _log_appid_errors(appid, "appdetails request failed", log_filepath)
        return {}

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
    appdetails["header_img"] = game_data.get("header_image")
    appdetails["screenshots"] = game_data.get("screenshots")
    appdetails["developers"] = game_data.get("developers")
    appdetails["publishers"] = game_data.get("publishers")
    appdetails["categories"] = game_data.get("categories")
    appdetails["genres"] = game_data.get("genres")
    appdetails["metacritic"] = game_data.get("metacritic")

    release_data = game_data.get("release_date",{})
    appdetails["release_date"] = format_date_string(release_data.get("date",""))
    if appdetails["release_date"] is None:
        _log_appid_errors(appid, f"failed to parse date: '{release_data.get("date","")}'", log_filepath)
        return {}
    
    return appdetails

def get_appreviewhistogram(appid, sesion, fecha_salida):
    """
    Obtiene y procesa estadísticas de reseñas de un juego en Steam. Extrae métricas
    generales y calcula el agregado de recomendaciones (positivas y negativas)
    correspondientes aproximadamente al primer mes de vida del juego.

    Args:
        appid (str): El ID del juego en Steam (APPID).
        sesion (requests.Session): Sesión ya abierta de requests.

    Returns:
        dict: Diccionario con las fechas de inicio/fin y los datos agregados de 'rollups'.
        Retorna un diccionario vacío si no hay datos disponibles.
    """
    log_filepath = error_log_path() / "log_reviewhist_error.jsonl"
    
    # Creamos la url
    url = "https://store.steampowered.com/appreviewhistogram/" + appid
    
    # Hacemos el request a la página y creamos el json que va a almacenar la info
    params_info = {"l": "english"}
    appreviewhistogram = {}
    
    # La función solicitud_url trata las distintas excepciones posibles
    data = _request_url(sesion, params_info, url)

    # Caso en el que no haya ninguna review: los rollups están vacíos
    if not data.get("results", "") or not data["results"].get("rollups",[]):
        _log_appid_errors(appid, "hist request failed", log_filepath)
        return {}

    appreviewhistogram["start_date"] = unix_to_date_string(data["results"]["start_date"])
    appreviewhistogram["end_date"] = unix_to_date_string(data["results"]["end_date"])
    appreviewhistogram["rollup_type"] = data["results"]["rollup_type"]

    # Buscamos que barra del histograma hay que coger
    idx = -1
    rollups = data["results"]["rollups"]
    for i in range(len(rollups)):
        rollup_dt = datetime.fromtimestamp(rollups[i].get("date"))
        if appreviewhistogram["rollup_type"] == "week":
            # Usamos .date() para asegurar que coincida el día ignorando la hora
            if rollup_dt.date() == fecha_salida.date(): # no va a coincidir casi nunca
                idx = i
                break
        else:
            if rollup_dt.year == fecha_salida.year and rollup_dt.month == fecha_salida.month:
                idx = i
                break

    if idx == -1:
        if len(rollups) == 0:
            return {}
        else:
            idx = 0

    # Cogemos los datos de aproximadamente el primer mes (las valoraciones del primer mes)
    if appreviewhistogram["rollup_type"] == "week":
        l = {"date": unix_to_date_string(rollups[idx].get("date")), "recommendations_up": 0, "recommendations_down": 0}
        for i in range(0, 4):
            if (idx + i) < len(rollups):
                l["recommendations_up"] += rollups[idx + i].get("recommendations_up", 0)
                l["recommendations_down"] += rollups[idx + i].get("recommendations_down", 0)
        appreviewhistogram["rollups"] = l
    else:
        # Si el dia es mayor que 15 y el primer mes no es el último del que se tiene información, se cogen también las del mes siguiente
        fecha = datetime.fromtimestamp(rollups[idx].get("date"))
        if fecha_salida.day > 15 and idx < len(rollups) - 1:
            # Número de dias que se tienen en cuenta
            # monthrange() devuelve (diaDeLaSemana, numDiasMes)
            dias_mes_actual = monthrange(fecha.year, fecha.month)[1] - fecha_salida.day + 1
            fecha_sig = datetime.fromtimestamp(rollups[idx + 1].get("date"))
            dias_mes_siguiente = monthrange(fecha_sig.year, fecha_sig.month)[1]
            dias = dias_mes_actual + dias_mes_siguiente
            rec_up = int(rollups[idx].get("recommendations_up", 0)) + int(rollups[idx + 1].get("recommendations_up", 0))
            rec_down = int(rollups[idx].get("recommendations_down", 0)) + int(rollups[idx + 1].get("recommendations_down", 0))
        else:
            dias = monthrange(fecha.year, fecha.month)[1] - fecha_salida.day + 1
            rec_up = int(rollups[idx].get("recommendations_up", 0))
            rec_down = int(rollups[idx].get("recommendations_down", 0))
        
        if dias == 0: 
            dias = 1
            
        appreviewhistogram["rollups"] = {
            "date": unix_to_date_string(rollups[idx].get("date")), 
            "recommendations_up": rec_up, 
            "recommendations_down": rec_down,
            "recommendations_up_per_day": round(rec_up / dias, 4),
            "recommendations_down_per_day": round(rec_down / dias, 4),
            "total_recommendations": rec_up + rec_down,
            "total_recommendations_per_day": round((rec_up + rec_down) / dias, 4),
            "dias":dias
        }

    return appreviewhistogram

if __name__ == "__main__":
    session = requests.Session()
    data = get_appdetails("730", session)
    filepath = data_path() / "test.json"
    write_to_file(data, filepath)