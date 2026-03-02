import requests
from random import uniform
import time
from tqdm import tqdm

from src.utils.config import steam_reviews_file
from src.utils.files import erase_file, write_to_file, file_exists
from src.utils.minio_server import upload_to_minio
from src.utils.exceptions import SteamAPIException

from utils_extraccion.steam_requests import get_resenyas
from utils_extraccion.sesion import get_pending_games, ask_overwrite_file, overwrite_confirmation, update_config


'''
Script que guarda la información procedente de appreviews

Requisitos:
Módulo requests para solicitar acceso a las APIs.

Entrada:
Necesita para su ejecución el archivo steam_apps.json

Salida:
Los datos se almacenan en la carpeta data/ en formato JSON.
'''

def _download_game_data(game, curr_idx, sesion):
    # Obtiene la info de un juego
    game["reviews"] = get_resenyas(game["id"], sesion, curr_idx < 100)

def D_informacion_resenyas(minio):
    # El objeto de la sesión mejora el rendimiento cuando se hacen muchas requests a un mismo host
    try:
        # por si da un error en get_pending_games, evitar un UnboundLocalError en el finally
        start_idx, curr_idx, end_idx = -1,-1,-1

        pending_games, start_idx, curr_idx, end_idx = get_pending_games("D", minio)
        
        if not pending_games:
            print(f"No hay juegos en el rango [{curr_idx}, {end_idx}]")
            return
        
        # Si existe fichero preguntar si sobreescribir o insertar al final, esta segunda opción no controla duplicados
        if file_exists(steam_reviews_file, minio):
            origen = " en MinIO" if minio["minio_read"] else ""
            mensaje = f"El fichero de reseñas ya existe{origen}:\n\n1. Añadir contenido al fichero existente\n2. Sobreescribir fichero\n\nIntroduce elección: "
            overwrite_file = ask_overwrite_file(mensaje)
            if overwrite_file:
                # asegurarse de que se quiere eliminar toda la información
                if overwrite_confirmation():
                    erase_file(steam_reviews_file, minio)
                else:
                    print("Operación cancelada")
                    return
                
        # comienzo de extracción
        sesion = requests.Session()
        sesion.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        print("Comenzando extraccion de juegos...\n")
        with tqdm(pending_games, unit = "games") as pbar:
            for game in pbar:
                appid = game.get("id")
                pbar.set_description(f"Procesando appid: {appid}")
                _download_game_data(game, curr_idx, sesion)
                write_to_file(game, steam_reviews_file)
                curr_idx += 1
                
    except SteamAPIException as e:
        print(e)
    except KeyboardInterrupt:
        print("\n\nDetenido por el usuario. Guardando antes de salir...")
    except Exception as e:
        print(f"Error inesperado durante descarga de información sobre el juego: {e}")    
    finally:
        if minio["minio_write"]: 
            corrrectly_uploaded = upload_to_minio(steam_reviews_file)
            if corrrectly_uploaded: erase_file(steam_reviews_file)
        
        reviews_file = {"start_idx" : start_idx, "curr_idx" : curr_idx, "end_idx" : end_idx}
        if curr_idx > end_idx:
            print("Rango completado")
        update_config("D", reviews_file)



if __name__ == "__main__":
    D_informacion_resenyas()