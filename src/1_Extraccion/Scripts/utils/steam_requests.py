import os
import requests
from tqdm import tqdm
from paths import data_path, error_log_path
from files import write_to_file
from date import format_date_string

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

    release_data = game_data.get("release_date",{}).get("date","")
    appdetails["release_date"] = format_date_string(release_data.get("date",""))
    if appdetails["release_date"] is None:
        _log_appid_errors(appid, f"failed to parse date: '{release_data.get("date","")}'", log_filepath)
        return {}
    
    return appdetails

if __name__ == "__main__":
    get_appids(100, 0)