import requests
import Z_funciones
from random import uniform
import time
import os
from tqdm import tqdm
from utils.steam_requests import get_resenyas
from utils.config import gamelist_file, steam_reviews_file
from utils.sesion import get_pending_games, tratar_existe_fichero, overwrite_confirmation, update_config
from utils.files import erase_file, write_to_file, log_appid_errors
from utils.exceptions import SteamAPIException

'''
Script que guarda la información procedente de appreviews

Requisitos:
Módulo requests para solicitar acceso a las APIs.

Entrada:
Necesita para su ejecución el archivo steam_apps.json

Salida:
Los datos se almacenan en la carpeta data/ en formato JSON.
'''

def _download_game_data(id, sesion):
    # Obtiene la info de un juego
    game_info = {"id": id, "resenyas": []}
    game_info["resenyas"] = get_resenyas(id, sesion)

    return game_info

def D_informacion_resenyas(minio = False):
    # El objeto de la sesión mejora el rendimiento cuando se hacen muchas requests a un mismo host
    try:
        # por si da un error en get_pending_games, evitar un UnboundLocalError en el finally
        start_idx, curr_idx, end_idx = -1,-1,-1

        pending_games, start_idx, curr_idx, end_idx = get_pending_games("D")
        
        if not pending_games:
            print(f"No hay juegos en el rango [{curr_idx}, {end_idx}]")
            return
        
        # Si existe fichero preguntar si sobreescribir o insertar al final, esta segunda opción no controla duplicados
        if os.path.exists(steam_reviews_file):
            mensaje = """El fichero de información de juegos ya existe:\n\n1. Añadir contenido al fichero existente
2. Sobreescribir fichero\n\nIntroduce elección: """
            overwrite = tratar_existe_fichero(mensaje)
            if overwrite:
                # asegurarse de que se quiere eliminar toda la información
                if overwrite_confirmation():
                    erase_file(steam_reviews_file)
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
                desc = _download_game_data(appid, sesion)
                write_to_file(desc, steam_reviews_file)
                wait = uniform(1.5, 2)
                time.sleep(wait)
                curr_idx += 1
                
    except SteamAPIException as e:
        print(e)
    except KeyboardInterrupt:
        print("\n\nDetenido por el usuario. Guardando antes de salir...")
    except Exception as e:
        print(f"Error inesperado durante descarga de información sobre el juego: {e}")    
    finally:
        reviews_file = {"start_idx" : start_idx, "curr_idx" : curr_idx, "end_idx" : end_idx}
        if curr_idx > end_idx:
            print("Rango completado")
        update_config("D", reviews_file)



if __name__ == "__main__":
    # Poner a True para traer y mandar los datos a MinIO
    D_informacion_resenyas(False)