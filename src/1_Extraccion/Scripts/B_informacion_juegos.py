import requests
import time
import os
from random import uniform
from tqdm import tqdm
from utils.steam_requests import get_appdetails, get_appreviewhistogram
from utils.exceptions import AppdetailsException, ReviewhistogramException, SteamAPIException
from utils.files import log_appid_errors, read_file, write_to_file
from utils.config import appidlist_file, appidlist_info_file, gamelist_file, gamelist_info_file, get_appid_range, config_file
from utils.sesion import handle_input, tratar_existe_fichero, read_config, update_config

'''
Script que guarda tanto la información de appdetails como de appreviewhistogram.

Requisitos:
- Módulo `requests` para solicitar acceso a las APIs.

Entrada:
- Necesita para su ejecución el archivo appids_list.json.gz y su información en el config.json

Salida:
- Los datos se almacenan en la carpeta data/ en formato JSONL comprimido.
'''

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
        \nLanza las siguientes excepciones en caso de fallo: AppdetailsException, ReviewhistogramException
    """
    # Datos iniciales
    game_info = {"id": appid, "appdetails": {}, "appreviewhistogram": {}}

    # Llamamos a funciones
    game_info["appdetails"] = get_appdetails(appid, session)
    release_date = game_info["appdetails"].get("release_date")
    game_info["appreviewhistogram"] = get_appreviewhistogram(appid, session, release_date)

    return game_info
    
def _get_session_info():
    """
    Comprueba si hay una sesión de extracción abierta leyendo el config y retorna los parámetros de la sesión
    si así lo quiere el usuario.

    :returns boolean, start_idx, curr_idx, end_idx:
    El booleano es True si se quiere usar la sesión y False en caso contrario.
    Devuelve indices de la sesión o dummies si no hay sesión o el usuario quiere una nueva sesión
    """
    # Parámetros de B
    gamelist_info = read_config("B")
    # Si existe sesión
    if gamelist_info is not None:
        message = f"Existe sesión de extracción [{gamelist_info.get('start_idx')}, {gamelist_info.get('end_idx')}] índice actual: {gamelist_info.get('curr_idx')}, quieres continuar con la sesión? [Y/N]: "
        response = handle_input(message, lambda x: x.lower() in {"y", "n"})
        # si quiere usar los parámetros de la sesión existente
        if response.lower() == "y":
            # devuelve los parámetros de la sesión y un booleano que indica la decsión del usuario
            start_idx, curr_idx, end_idx = gamelist_info["start_idx"], gamelist_info["curr_idx"], gamelist_info["end_idx"]
            return True, start_idx, curr_idx, end_idx
    # Si no hay sesión devuelve valores dummy
    return False, -1, -1 ,-1

def get_pending_games():
    # leer la lista de appids
    appidlist = read_file(appidlist_file)
    # inicializar indices dummy
    start_idx, curr_idx, end_idx = -1, -1, -1
    # si no hay lista de juegos devolver una lista vacía
    if appidlist is None:
        return [], start_idx, curr_idx, end_idx 

    continue_session, start_idx, curr_idx, end_idx = _get_session_info()
    # si se quiere usar información de sesión existente
    if continue_session:
        return appidlist[curr_idx:end_idx+1], start_idx, curr_idx, end_idx
    
    # si no se quiere usar sesión existente o no hay sesión existente
    print("Configurando nueva sesión...\n")
    # muestra rangos disponibles de la lista
    appidlist_info = read_config("A") 
    print(f"Tamaño lista de juegos: {appidlist_info.get('size', 0)}")
    print(f"Rango de índices disponibles: [0, {appidlist_info.get('size', 0)-1}]")

    message = """Opciones: \n\n1. Elegir rango manualmente\n2. Extraer rango correspondiente al identificador\n
Introduce elección: """
    option = handle_input(message, lambda x: x in {"1", "2"})

    if option == "1": # Elegir rango manualmente
        def _isValidStart(response):
            return response.isdigit() and int(response) >= 0 and int(response) < appidlist_info.get("size", 0)
        message = f"Introduce índice inicial [0, {appidlist_info.get('size', 0)-1}]: "
        start_idx = int(handle_input(message,_isValidStart))
        curr_idx = start_idx

        def _isValidEnd(response):
            return response.isdigit() and int(response) >= start_idx and int(response) <= appidlist_info.get('size', 0)-1
        message = f"Introduce índice final [{start_idx}, {appidlist_info.get('size', 0)-1}]: "
        end_idx = int(handle_input(message,_isValidEnd))
        
    elif option == "2": # usar rango del identificador, si no hay identificador, se hace completo
        start_idx, curr_idx, end_idx = get_appid_range(appidlist_info["size"])
    
    return appidlist[curr_idx:end_idx+1], start_idx, curr_idx, end_idx

def _overwrite_confirmation():
    message = "¿Seguro que quieres eliminar la lista de juegos con su información [Y/N]?: "
    response = handle_input(message, lambda x: x.lower() in {"y", "n"})
    return True if response.lower() == "y" else False

def B_informacion_juegos(minio = False): # PARA TERMINAR SESIÓN: CTRL + C
    try:
        # por si da un error en get_pending_games, evitar un UnboundLocalError en el finally
        start_idx, curr_idx, end_idx = -1,-1,-1

        pending_games, start_idx, curr_idx, end_idx = get_pending_games()
        
        if not pending_games:
            print(f"No hay juegos en el rango [{curr_idx}, {end_idx}]")
            return
        
        # Si existe fichero preguntar si sobreescribir o insertar al final, esta segunda opción no controla duplicados
        if os.path.exists(gamelist_file):
            mensaje = """El fichero de información de juegtos ya existe:\n\n1. Añadir contenido al fichero existente
2. Sobreescribir fichero\n\nIntroduce elección: """
            overwrite = tratar_existe_fichero(mensaje)
            if overwrite:
                # asegurarse de que se quiere eliminar toda la información
                if _overwrite_confirmation():
                    os.remove(gamelist_file)
                else:
                    print("Operación cancelada")
                    return
                
        # comienzo de extracción
        sesion = requests.Session()
        sesion.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        print("Comenzando extraccion de juegos...\n")
        with tqdm(pending_games, unit = "appids") as pbar:
            for appid in pbar:
                pbar.set_description(f"Procesando appid: {appid}")
                try:
                    desc = download_game_data(appid, sesion)
                    write_to_file(desc, gamelist_file)
                    wait = uniform(1.5, 2)
                    time.sleep(wait)
                except(AppdetailsException, ReviewhistogramException) as e:
                    pbar.write(str(e))
                    log_appid_errors(e.appid, str(e))
                finally:
                    curr_idx += 1
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
        update_config("B", gamelist_info)
    

if __name__ == "__main__":
    # Poner a True para traer y mandar los datos a MinIO
    B_informacion_juegos(False)