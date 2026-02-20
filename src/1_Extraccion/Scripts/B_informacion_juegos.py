import requests
import time
from numpy.random import choice, uniform
from utils.webscraping import user_agents
from tqdm import tqdm
from utils.steam_requests import get_appdetails, get_appreviewhistogram
from utils.exceptions import AppdetailsException, ReviewhistogramException, SteamAPIException
from utils.files import log_appid_errors, write_to_file, erase_file, read_file, file_exists
from utils.config import gamelist_file
from utils.sesion import tratar_existe_fichero, update_config, get_pending_games, overwrite_confirmation
from utils.minio_server import upload_to_minio

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

def B_informacion_juegos(minio): # PARA TERMINAR SESIÓN: CTRL + C
    """
    Obtiene la información de los juegos especificados en el fichero appids_list.json.gz

    Args:
        minio (dic): diccionario de la forma {"minio_write": False, "minio_read": False} para activar y desactivar subida y bajada de MinIO
    
    Returns:
        None
    """
    try:
        # por si da un error en get_pending_games, evitar un UnboundLocalError en el finally
        start_idx, curr_idx, end_idx = -1,-1,-1

        pending_games, start_idx, curr_idx, end_idx = get_pending_games("B", minio)
        
        if not pending_games:
            print(f"No hay juegos en el rango [{curr_idx}, {end_idx}]")
            return
        
        # Si existe fichero preguntar si sobreescribir o insertar al final, esta segunda opción no controla duplicados
        if file_exists(gamelist_file, minio):
            origen = " en MinIO" if minio["minio_read"] else ""
            mensaje = f"El fichero de lista de appids ya existe{origen}:\n\n1. Añadir contenido al fichero existente\n2. Sobreescribir fichero\n\nIntroduce elección: "
            overwrite_file = tratar_existe_fichero(mensaje)
            if overwrite_file:
                # asegurarse de que se quiere eliminar toda la información
                if overwrite_confirmation():
                    erase_file(gamelist_file, minio)
                else:
                    print("Operación cancelada")
                    return
                
        # comienzo de extracción
        sesion = requests.Session()
        user_agent = choice(user_agents)
        sesion.headers.update({'User-Agent': user_agent})
        print("Comenzando extraccion de juegos...\n")
        with tqdm(pending_games, unit = "appids") as pbar:
            for appid in pbar:
                pbar.set_description(f"Procesando appid {appid}")
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
        if minio["minio_write"]: 
            corrrectly_uploaded = upload_to_minio(gamelist_file)
            if corrrectly_uploaded: erase_file(gamelist_file)

        gamelist_info = {"start_idx" : start_idx, "curr_idx" : curr_idx, "end_idx" : end_idx}
        if curr_idx > end_idx:
            print("Rango completado")
        update_config("B", gamelist_info)
    

if __name__ == "__main__":
    B_informacion_juegos()