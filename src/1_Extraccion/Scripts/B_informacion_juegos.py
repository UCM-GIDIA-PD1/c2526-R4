import requests
import time
import os
from random import uniform
from tqdm import tqdm
from utils.steam_requests import get_appdetails, get_appreviewhistogram
from utils.exceptions import AppdetailsException, ReviewhistogramException, SteamAPIException
from utils.files import log_appid_errors, read_file, write_to_file
from utils.config import appidlist_file, appidlist_info_file, gamelist_file, gamelist_info_file, get_appid_range

'''
Script que guarda tanto la información de appdetails como de appreviewhistogram.

Requisitos:
- Módulo `requests` para solicitar acceso a las APIs.

Entrada:
- Necesita para su ejecución el archivo steam_apps.json.gz

Salida:
- Los datos se almacenan en la carpeta data/ en formato JSON comprimido.
'''

def _handle_input(initial_message, isResponseValid = lambda x: True):
    """
    Función que maneja la entrada. Por defecto la función siempre devuelve True.

    Args:
        mensaje (str): mensaje inicial. 
        isResponseValid (function): función que verifica la validez de un input dado.

    Returns:
        boolean: True si el input es correcto, false en caso contrario.
    """
    respuesta = input(initial_message).strip()

    # Hasta que no se dé una respuesta válida no se puede salir del bucle
    while not isResponseValid(respuesta):
        respuesta = input("Opción no válida, prueba de nuevo: ").strip()
    
    return respuesta

def _tratar_existe_fichero():
    """
    Menú con opción de añadir contenido al fichero existente o sobreescribirlo.
    
    returns:
        boolean: True si sobreescribir archivo meter appids nuevos, False en caso contrario
    """

    mensaje = """El fichero de lista de appids ya existe:\n\n1. Añadir contenido al fichero existente 
2. Sobreescribir fichero\n\nIntroduce elección: """

    def _isValid(respuesta):
        valid_inputs ={"1", "2"}
        return respuesta in valid_inputs

    respuesta = _handle_input(mensaje, _isValid)
    return True if respuesta == "2" else False

def download_game_data(appid, session):
    """
    Fusiona la descarga completa de información de un juego usando varias funciones.
    Agrega los detalles del producto y el histograma de reseñas en un único objeto.
    Si alguna de las fuentes de datos críticas está vacía, el juego se descarta.

    Args:
        appid: Identificador numérico del juego en Steam.
        session (requests.Session): Sesión persistente para las peticiones HTTP.

    Returns:
        dict: Diccionario estructurado con 'id', 'appdetails' y 'appreviewhistogram'.
        Retorna un diccionario vacío si falla la obtención de cualquiera de las partes.
    """
    # Datos iniciales
    game_info = {"id": appid, "appdetails": {}, "appreviewhistogram": {}}

    # Llamamos a funciones
    game_info["appdetails"] = get_appdetails(appid, session)
    release_date = game_info["appdetails"].get("release_date")
    game_info["appreviewhistogram"] = get_appreviewhistogram(appid, session, release_date)

    return game_info
    
def get_pending_games():
    appidlist = read_file(appidlist_file)

    if appidlist is None:
        return 0, -1

    if os.path.exists(gamelist_info_file):
        gamelist_info = read_file(gamelist_info_file)
        start_idx, curr_idx, end_idx = gamelist_info["start_idx"], gamelist_info["curr_idx"], gamelist_info["end_idx"]
        message = f"Existe sesión de extracción [{gamelist_info.get("start_idx")}, {gamelist_info.get("end_idx")}], quieres continuar con la sesión? [Y/N]: "

        def _isValid(response):
            return response.lower() in {"y", "n"}
        response = _handle_input(message, _isValid)

        if response.lower() == "y":
            return appidlist[curr_idx : end_idx+1], start_idx, curr_idx, end_idx
        else:
            print("Configurando nueva sesión...\n")

    appidlist_info = read_file(appidlist_info_file)

    print(f"Tamaño lista de juegos: {appidlist_info.get('size', 0)}")
    print(f"Rango de índices disponibles: [0, {appidlist_info.get('size', 0)-1}]")

    message = """Opciones: \n\n1. Elegir rango manualmente\n2. Extraer rango correspondiente al identificador\n
Introduce elección: """

    def _isValid(response):
        return response in {"1", "2"}
    option = _handle_input(message, _isValid)

    if option == "1":
        def _isValid(response):
            return response.isdigit() and int(response) >= 0 and int(response) < appidlist_info.get("size", 0)
        message = f"Introduce índice inicial [0, {appidlist_info.get('size', 0)-1}]: "
        start_idx = int(_handle_input(message,_isValid))
        curr_idx = start_idx
        def _isValid(response):
            return response.isdigit() and int(response) >= start_idx and int(response) <= end_idx
        message = f"Introduce índice final [{start_idx}, {appidlist_info.get('size', 0)-1}]:"
        end_idx = int(_handle_input(message,_isValid))
        
    elif option == "2":
        start_idx, curr_idx, end_idx = get_appid_range(appidlist_info["size"])
    
    return appidlist[start_idx:end_idx+1], start_idx, curr_idx, end_idx

def _overwrite_confirmation():
    def _isValid(response):
        return response.lower() in {"y", "n"}
    message = "¿Seguro que quieres eliminar la lista de juegos con su información [Y/N]?: "
    response = _handle_input(message, _isValid)
    return True if response.lower() == "y" else False

def B_informacion_juegos(minio = False): # PARA TERMINAR SESIÓN: CTRL + C
    # Cargamos los datos
    try:
        pending_games, start_idx, curr_idx, end_idx = get_pending_games()
        
        if os.path.exists(gamelist_file):
            overwrite = _tratar_existe_fichero()
            if overwrite:
                if _overwrite_confirmation():
                    os.remove(gamelist_file)
                else:
                    print("Operación cancelada")
                    return
                
        if not pending_games:
            print(f"No hay juegos en el rango [{curr_idx}, {end_idx}]")
            return

        sesion = requests.Session()
        sesion.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

        print("Comenzando extraccion de juegos...\n")
        with tqdm(pending_games, unit = "appids") as pbar:
            for appid in pbar:
                pbar.set_description(f"Procesando appid: {appid}")
                try:
                    desc = download_game_data(appid, sesion)
                    write_to_file(desc, gamelist_file)
                    curr_idx += 1
                    wait = uniform(1.5, 2)
                    time.sleep(wait)
                except(AppdetailsException, ReviewhistogramException) as e:
                    pbar.write(e)
                    log_appid_errors(e.appid, e)
    except SteamAPIException as e:
        print(e)
    except KeyboardInterrupt:
        print("\n\nDetenido por el usuario. Guardando antes de salir...")
    except Exception as e:
        print(f"Error inesperado durante descarga de información sobre el juego: {e}")
    finally:
        gamelist_info = {"start_idx" : start_idx, "curr_idx" : curr_idx, "end_idx" : end_idx}
        if curr_idx > end_idx:
            print("Rango completado")
        write_to_file(gamelist_info, gamelist_info_file)
    

if __name__ == "__main__":
    # Poner a True para traer y mandar los datos a MinIO
    B_informacion_juegos(False)