import requests
from bs4 import BeautifulSoup
import Z_funciones

'''
Script que guarda tanto la información de appdetails como de appreviewhistogram.

Requisitos:
- Módulo `requests` para solicitar acceso a las APIs.

Entrada:
- Necesita para su ejecución el archivo steam_apps.json

Salida:
- Los datos se almacenan en la carpeta data/ en formato JSON.
'''

def get_appdetails(str_id, sesion):
    """
    Extrae y limpia los detalles técnicos y comerciales de un juego desde la API de Steam.

    Args:
        str_id (str): ID de la aplicación (AppID) en Steam.
        sesion (requests.Session): Sesión persistente para realizar la petición HTTP.

    Returns:
        dict: Diccionario con la información procesada (nombre, precio, idiomas, etc.).
        Retorna un diccionario vacío si la petición falla o el ID no es válido.
    """
    # Creamos la url
    url = "https://store.steampowered.com/api/appdetails?appids=" + str_id

    # Hacemos el request a la página y creamos el json que va a almacenar la info
    params_info = {"cc": "eur"}
    appdetails = {}
    data = Z_funciones.solicitud_url(sesion, params_info, url)
    if not data:
        return appdetails

    # Metemos la información útil
    appdetails["name"] = data[str_id]["data"].get("name")
    appdetails["required_age"] = data[str_id]["data"].get("required_age")
    appdetails["short_description"] = data[str_id]["data"].get("short_description")
    if not data[str_id]["data"].get("price_overview"):
        # Si el juego no tiene price_overview significa que es gratis, por lo que 
        # metemos nosotros los valores a 0
        appdetails["price_overview"] = {}
        appdetails["price_overview"]["currency"] = "EUR"
        appdetails["price_overview"]["initial"] = 0
        appdetails["price_overview"]["final"] = 0
        appdetails["price_overview"]["discount_percent"] = 0
        appdetails["price_overview"]["initial_formatted"] = ""
        appdetails["price_overview"]["final_formatted"] = "0€"
    else:
        # Si el juego no es gratis copiamos el price_overview directamente de data
        appdetails["price_overview"] = data[str_id]["data"].get("price_overview")

    # Limpiamos los lenguajes a los que están traducidos el juego
    if data[str_id]["data"].get("supported_languages"):
        languages_raw_bs4 = BeautifulSoup(data[str_id]["data"].get("supported_languages"), features="lxml").text
        clean_text = str(languages_raw_bs4).replace("idiomas con localización de audio", "").replace("*", "")
        appdetails["supported_languages"] = list({lang.strip() for lang in clean_text.split(",")})

    # Copiamos más información
    appdetails["capsule_img"] = data[str_id]["data"].get("capsule_imagev5")
    appdetails["header_img"] = data[str_id]["data"].get("header_image")
    appdetails["screenshots"] = data[str_id]["data"].get("screenshots")

    appdetails["developers"] = data[str_id]["data"].get("developers")
    appdetails["publishers"] = data[str_id]["data"].get("publishers")

    appdetails["categories"] = data[str_id]["data"].get("categories")
    appdetails["genres"] = data[str_id]["data"].get("genres")
    appdetails["metacritic"] = data[str_id]["data"].get("metacritic")

    appdetails["release_date"] = data[str_id]["data"].get("release_date")

    return appdetails

def get_appreviewhistogram(str_id, sesion):
    """
    Obtiene y procesa estadísticas de reseñas de un juego en Steam. Extrae métricas
    generales y calcula el agregado de recomendaciones (positivas y negativas)
    correspondientes aproximadamente al primer mes de vida del juego.

    Args:
        str_id (str): El ID del juego en Steam (APPID).
        sesion (requests.Session): Sesión ya abierta de requests.

    Returns:
        dict: Diccionario con las fechas de inicio/fin y los datos agregados de 'rollups'.
        Retorna un diccionario vacío si no hay datos disponibles.
    """
    # Creamos la url
    url = "https://store.steampowered.com/appreviewhistogram/" + str_id
    
    # Hacemos el request a la página y creamos el json que va a almacenar la info
    params_info = {"l": "english"}
    appreviewhistogram = {}
    data = Z_funciones.solicitud_url(sesion, params_info, url)

    # Caso en el que no haya ninguna review: los rellups están vacíos
    if not data:
        return appreviewhistogram
    if not data["results"].get("rollups"):
        return appreviewhistogram

    appreviewhistogram["start_date"] = data["results"]["start_date"]
    appreviewhistogram["end_date"] = data["results"]["end_date"]
    appreviewhistogram["rollup_type"] = data["results"]["rollup_type"]

    # Cogemos los datos de aproximadamente el primer mes (las valoraciones del primer mes)
    if appreviewhistogram["rollup_type"] == "week":
        l = {"date": data["results"]["rollups"][0].get("date"), "recommendations_up": 0, "recommendations_down": 0}
        for i in range(0, 4):
            if data["results"]["rollups"].get(i):
                l["recommendations_up"] += data["results"]["rollups"][i].get("recommendations_up")
                l["recommendations_down"] += data["results"]["rollups"][i].get("recommendations_down")
        appreviewhistogram["rollups"] = l
    else:
        appreviewhistogram["rollups"] = {"date": data["results"]["rollups"][0].get("date"), 
             "recommendations_up": data["results"]["rollups"][0].get("recommendations_up"), 
             "recommendations_down": data["results"]["rollups"][0].get("recommendations_down")}

    return appreviewhistogram

def descargar_datos_juego(id, sesion):
    """
    Fusiona la descarga completa de información de un juego usando varias funciones.
    Agrega los detalles del producto y el histograma de reseñas en un único objeto.
    Si alguna de las fuentes de datos críticas está vacía, el juego se descarta.

    Args:
        id (int): Identificador numérico del juego en Steam.
        sesion (requests.Session): Sesión persistente para las peticiones HTTP.

    Returns:
        dict: Diccionario estructurado con 'id', 'appdetails' y 'appreviewhistogram'.
        Retorna un diccionario vacío si falla la obtención de cualquiera de las partes.
    """
    # Datos iniciales
    game_info = {"id": id, "appdetails": {}, "appreviewhistogram": {}}
    str_id = str(id)

    # Llamamos a funciones
    game_info["appdetails"] = get_appdetails(str_id, sesion)
    game_info["appreviewhistogram"] = get_appreviewhistogram(str_id, sesion)

    if game_info["appreviewhistogram"] == {} or game_info["appdetails"] == {}:
        # Si el appreviewhistogram está vacío, significa que el juego no tiene reseñas
        return {}
    else:
        return game_info

def main():
    # Abrimos sesión de requests
    sesion = requests.Session()

    # Cargamos el json de la lista de juegos (archivo de lista_juegos.py)
    lista_juegos = Z_funciones.cargar_datos_locales(r"data\steam_apps.json")
    
    # Iteramos sobre la lista de juegos y lo metemos en un json nuevo
    print("Comenzando extraccion de juegos...\n")
    informacion_juegos = {"data":[]}
    for juego in lista_juegos.get("apps"):
        desc = descargar_datos_juego(juego.get("appid"), sesion)
        if desc != {}:
            informacion_juegos["data"].append(desc)
            print(f"{juego["appid"]}: {juego["name"]}")
    
    # Metemos la información en un json
    Z_funciones.guardar_datos_json(informacion_juegos, r"data\info_steam_games.json")

if __name__ == "__main__":
    main()