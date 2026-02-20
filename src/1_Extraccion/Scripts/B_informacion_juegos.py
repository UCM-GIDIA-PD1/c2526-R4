import requests
import time
import os
from random import uniform
from tqdm import tqdm
from utils.steam_requests import get_appdetails, get_appreviewhistogram
from utils.exceptions import AppdetailsException, ReviewhistogramException, SteamAPIException
from utils.files import log_appid_errors, write_to_file, erase_file
from utils.config import gamelist_file
from utils.sesion import tratar_existe_fichero, update_config, get_pending_games, overwrite_confirmation

'''
Script que guarda tanto la información de appdetails como de appreviewhistogram.

Requisitos:
- Módulo `requests` para solicitar acceso a las APIs.

Entrada:
- Necesita para su ejecución el archivo appids_list.json.gz y su información en el config.json

Salida:
- Los datos se almacenan en la carpeta data/ en formato JSONL comprimido.
'''

def _download_game_data(appid, session):
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

def B_informacion_juegos(minio = False): # PARA TERMINAR SESIÓN: CTRL + C
    try:
        # por si da un error en get_pending_games, evitar un UnboundLocalError en el finally
        start_idx, curr_idx, end_idx = -1,-1,-1

        pending_games, start_idx, curr_idx, end_idx = get_pending_games("B")
        
        if not pending_games:
            print(f"No hay juegos en el rango [{curr_idx}, {end_idx}]")
            return
        
        # Si existe fichero preguntar si sobreescribir o insertar al final, esta segunda opción no controla duplicados
        if os.path.exists(gamelist_file):
            mensaje = """El fichero de información de juegos ya existe:\n\n1. Añadir contenido al fichero existente
2. Sobreescribir fichero\n\nIntroduce elección: """
            overwrite = tratar_existe_fichero(mensaje)
            if overwrite:
                # asegurarse de que se quiere eliminar toda la información
                if overwrite_confirmation():
                    erase_file(gamelist_file)
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
                    desc = _download_game_data(appid, sesion)
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