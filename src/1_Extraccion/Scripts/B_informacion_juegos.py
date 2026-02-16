import requests
from bs4 import BeautifulSoup
from Z_funciones import solicitud_url, convertir_fecha_datetime, abrir_sesion, guardar_datos_dict, cerrar_sesion, log_fallos
import time
from datetime import datetime
from calendar import monthrange
from random import uniform
from tqdm import tqdm

'''
Script que guarda tanto la información de appdetails como de appreviewhistogram.

Requisitos:
- Módulo `requests` para solicitar acceso a las APIs.

Entrada:
- Necesita para su ejecución el archivo steam_apps.json.gz

Salida:
- Los datos se almacenan en la carpeta data/ en formato JSON comprimido.
'''

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
    data = solicitud_url(sesion, params_info, url)

    if not data.get(appid, "") or not data[appid].get("success", False):
        return appdetails

    data_game = data[appid]["data"]

    # Metemos la información útil
    appdetails["name"] = data_game.get("name")
    appdetails["required_age"] = data_game.get("required_age")
    appdetails["short_description"] = data_game.get("short_description")
    appdetails["header_url"] = data_game.get("header_image")
    
    if not data_game.get("price_overview"):
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
        appdetails["price_overview"] = data_game.get("price_overview")

    # Limpiamos los lenguajes a los que están traducidos el juego
    if data_game.get("supported_languages"):
        try:
            languages_raw_bs4 = BeautifulSoup(data_game.get("supported_languages"), features="lxml").text
            clean_text = str(languages_raw_bs4).replace("idiomas con localización de audio", "").replace("*", "")
            appdetails["supported_languages"] = list({lang.strip() for lang in clean_text.split(",")})
        except:
            appdetails["supported_languages"] = []

    # Copiamos más información
    appdetails["capsule_img"] = data_game.get("capsule_imagev5")
    appdetails["header_img"] = data_game.get("header_image")
    appdetails["screenshots"] = data_game.get("screenshots")

    appdetails["developers"] = data_game.get("developers")
    appdetails["publishers"] = data_game.get("publishers")

    appdetails["categories"] = data_game.get("categories")
    appdetails["genres"] = data_game.get("genres")
    appdetails["metacritic"] = data_game.get("metacritic")

    appdetails["release_date"] = data_game.get("release_date")

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
    # Creamos la url
    url = "https://store.steampowered.com/appreviewhistogram/" + appid
    
    # Hacemos el request a la página y creamos el json que va a almacenar la info
    params_info = {"l": "english"}
    appreviewhistogram = {}
    
    # La función solicitud_url trata las distintas excepciones posibles
    data = solicitud_url(sesion, params_info, url)

    # Caso en el que no haya ninguna review: los rollups están vacíos
    if not data.get("results", "") or not data["results"].get("rollups",[]):
        return appreviewhistogram

    appreviewhistogram["start_date"] = data["results"]["start_date"]
    appreviewhistogram["end_date"] = data["results"]["end_date"]
    appreviewhistogram["rollup_type"] = data["results"]["rollup_type"]

    # Buscamos que barra del histograma hay que coger
    idx = -1
    rollups = data["results"]["rollups"]
    for i in range(len(rollups)):
        rollup_dt = datetime.fromtimestamp(rollups[i].get("date"))
        if appreviewhistogram["rollup_type"] == "week":
            # Usamos .date() para asegurar que coincida el día ignorando la hora
            if rollup_dt.date() == fecha_salida.date():
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
        l = {"date": rollups[idx].get("date"), "recommendations_up": 0, "recommendations_down": 0}
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
            "date": rollups[idx].get("date"), 
            "recommendations_up": rec_up, 
            "recommendations_down": rec_down,
            "recommendations_up_per_day": rec_up / dias,
            "recommendations_down_per_day": rec_down / dias,
            "total_recommendations": rec_up + rec_down,
            "total_recommendations_per_day": (rec_up + rec_down) / dias,
            "dias":dias
        }

    return appreviewhistogram

def descargar_datos_juego(appid, sesion):
    """
    Fusiona la descarga completa de información de un juego usando varias funciones.
    Agrega los detalles del producto y el histograma de reseñas en un único objeto.
    Si alguna de las fuentes de datos críticas está vacía, el juego se descarta.

    Args:
        appid: Identificador numérico del juego en Steam.
        sesion (requests.Session): Sesión persistente para las peticiones HTTP.

    Returns:
        dict: Diccionario estructurado con 'id', 'appdetails' y 'appreviewhistogram'.
        Retorna un diccionario vacío si falla la obtención de cualquiera de las partes.
    """
    # Datos iniciales
    game_info = {"id": appid, "appdetails": {}, "appreviewhistogram": {}}

    # Llamamos a funciones
    game_info["appdetails"] = get_appdetails(appid, sesion)

    release_data = game_info["appdetails"].get("release_date")
    
    # Verificación estricta para que no falle si la fecha viene mal formada o es None
    if not release_data or not isinstance(release_data, dict) or not release_data.get("date"):
        return {}
    
    fecha_salida_datetime = convertir_fecha_datetime(release_data.get("date"))

    if not fecha_salida_datetime:
        return {}
    
    game_info["appreviewhistogram"] = get_appreviewhistogram(appid, sesion, fecha_salida_datetime)

    return game_info

def B_informacion_juegos(): # PARA TERMINAR SESIÓN: CTRL + C
    # Cargamos los datos
    origin = "steam_apps.json.gz"
    final = "info_steam_games.json.gz"
    juego_ini, juego_fin, juegos_pendientes, ruta_temp_jsonl, ruta_final_gzip, ruta_config = abrir_sesion(origin, final)
    
    if juego_ini is None:
        return

    # Creamos sesión con user-Agent para parecer un navegador (es recomendable cambiarlo si no se trabaja en Windows)
    sesion = requests.Session()
    sesion.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}) 
    
    # Iteramos sobre la lista de juegos y lo metemos en un JSON nuevo
    print("Comenzando extraccion de juegos...\n")
    idx_actual = juego_ini
    try:
        with tqdm(juegos_pendientes, unit = "appids") as pbar:
            for appid in pbar:
                pbar.set_description(f"Procesando appid: {appid}")

                try:
                    desc = descargar_datos_juego(appid, sesion)
                    
                    if desc:
                        guardar_datos_dict(desc, ruta_temp_jsonl)
                    else:
                        log_fallos(appid, "appdetails: contenido filtrado")
                        print(f"\nError procesando juego {appid}: contenido filtrado")
                    wait = uniform(1.5, 2.5)
                    time.sleep(wait)
                    
                except Exception as e:
                    # Si falla un juego específico, lo logueamos y seguimos con el siguiente
                    log_fallos(appid, "appdetails: " + str(e))
                    print(f"\nError procesando juego {appid}: {e}")

                idx_actual += 1
    except KeyboardInterrupt:
        print("\n\nDetenido por el usuario. Guardando antes de salir...")
    finally:
        cerrar_sesion(ruta_temp_jsonl, ruta_final_gzip, ruta_config, idx_actual, juego_fin)

if __name__ == "__main__":
    B_informacion_juegos()