import requests
from bs4 import BeautifulSoup
import Z_funciones
import time
import os
import json
from datetime import datetime

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
    
    try:
        data = Z_funciones.solicitud_url(sesion, params_info, url)
    except Exception:
        return appdetails

    if not data or not data.get(str_id) or not data[str_id]["success"]:
        return appdetails

    data_game = data[str_id]["data"]

    # Metemos la información útil
    appdetails["name"] = data_game.get("name")
    appdetails["required_age"] = data_game.get("required_age")
    appdetails["short_description"] = data_game.get("short_description")
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

def get_appreviewhistogram(str_id, sesion, fecha_salida):
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
    
    try:
        data = Z_funciones.solicitud_url(sesion, params_info, url)
    except Exception:
        return appreviewhistogram

    # Caso en el que no haya ninguna review: los rellups están vacíos
    if not data or not data.get("results") or not data["results"].get("rollups"):
        return appreviewhistogram

    appreviewhistogram["start_date"] = data["results"]["start_date"]
    appreviewhistogram["end_date"] = data["results"]["end_date"]
    appreviewhistogram["rollup_type"] = data["results"]["rollup_type"]

    # Buscamos que histograma hay que coger
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
        return {}

    # Cogemos los datos de aproximadamente el primer mes (las valoraciones del primer mes)
    if appreviewhistogram["rollup_type"] == "week":
        l = {"date": rollups[idx].get("date"), "recommendations_up": 0, "recommendations_down": 0}
        for i in range(0, 4):
            if (idx + i) < len(rollups):
                l["recommendations_up"] += rollups[idx + i].get("recommendations_up", 0)
                l["recommendations_down"] += rollups[idx + i].get("recommendations_down", 0)
        appreviewhistogram["rollups"] = l
    else:
        appreviewhistogram["rollups"] = {
            "date": rollups[idx].get("date"), 
            "recommendations_up": rollups[idx].get("recommendations_up", 0), 
            "recommendations_down": rollups[idx].get("recommendations_down", 0)
        }

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

    release_data = game_info["appdetails"].get("release_date")
    
    # Verificación estricta para que no falle si la fecha viene mal formada o es None
    if not release_data or not isinstance(release_data, dict) or not release_data.get("date"):
        return {}
    
    fecha_salida_datetime = Z_funciones.convertir_fecha_datetime(release_data.get("date"))
    
    if not fecha_salida_datetime:
        return {}

    game_info["appreviewhistogram"] = get_appreviewhistogram(str_id, sesion, fecha_salida_datetime)

    if game_info["appreviewhistogram"] == {}:
        # Si el appreviewhistogram está vacío, significa que el juego no tiene reseñas
        return {}
    else:
        return game_info

def main():
    sesion = requests.Session()
    # User-Agent para parecer un navegador
    sesion.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}) 

    ruta_origen = r"data\steam_apps.json"
    ruta_destino = r"data\info_steam_games.json"
    
    # Cargamos el json de la lista de juegos
    lista_juegos = Z_funciones.cargar_datos_locales(ruta_origen)
    if not lista_juegos:
        print("No se encontró la lista de appids")
        return
    
    ids_procesados = set()
    if os.path.exists(ruta_destino):
        print('Reanudando progreso...')
        data_existente = Z_funciones.cargar_datos_locales(ruta_destino)
        if data_existente and "data" in data_existente:
            ids_procesados = {j["id"] for j in data_existente["data"]}

    print(f"Total juegos: {len(lista_juegos['apps'])} | Ya procesados: {len(ids_procesados)}")
    
    # Iteramos sobre la lista de juegos y lo metemos en un json nuevo
    print("Comenzando extraccion de juegos...\n")
    
    batch_juegos = []

    try:
        for juego in lista_juegos.get("apps"):
            appid = juego.get("appid")
            
            # Saltamos los procesados
            if appid in ids_procesados:
                continue

            try:
                desc = descargar_datos_juego(appid, sesion)
                
                if desc != {}:
                    batch_juegos.append(desc)
                    ids_procesados.add(appid)
                    print(f"{appid}: {juego.get('name')}")
                    
                    if len(batch_juegos) >= 20:
                        # Cada 20 juegos los añade al json para no saturar la RAM
                        datos_totales = Z_funciones.cargar_datos_locales(ruta_destino)
                        if not datos_totales:
                            datos_totales = {"data": []}
                        
                        datos_totales["data"].extend(batch_juegos)
                        Z_funciones.guardar_datos_json(datos_totales, ruta_destino)
                        
                        batch_juegos = [] # Vaciamos memoria
                        print(f"Progreso guardado automáticamente ({len(ids_procesados)} juegos)")

                # Pausa para respetar la API
                time.sleep(1.5)

            except Exception as e:
                # Si falla un juego específico, lo logueamos y seguimos con el siguiente
                print(f"Error procesando juego {appid}: {e}")
                continue

    except KeyboardInterrupt:
        print("\nDetenido por el usuario. Guardando antes de salir...")
    finally:
        # Guardado final de lo que quede en el batch
        if batch_juegos:
            datos_totales = Z_funciones.cargar_datos_locales(ruta_destino)
            if not datos_totales:
                datos_totales = {"data": []}
            datos_totales["data"].extend(batch_juegos)
            Z_funciones.guardar_datos_json(datos_totales, ruta_destino)
        
        print("Sesión finalizada.")

if __name__ == "__main__":
    main()