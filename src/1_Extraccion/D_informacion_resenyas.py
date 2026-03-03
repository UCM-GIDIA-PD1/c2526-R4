"""
Script que guarda en data/raw un JSON comprimido de las reviews de los juegos de Steam provenientes de los ficheros
rest_games_total_reviews.json.gz y top_100_games_total_reviews.json.gz, obtenidos de D1_games_reviews_filter

Requisitos:
- Archivo rest_games_total_reviews.json.gz
- Archivo top_100_games_total_reviews.json.gz
"""

import requests
from tqdm import tqdm
from numpy.random import choice

from src.utils.config import steam_reviews_file
from src.utils.files import erase_file, write_to_file, file_exists
from src.utils.minio_server import upload_to_minio
from src.utils.exceptions import SteamAPIException

from utils_extraccion.webscraping import user_agents
from utils_extraccion.steam_requests import get_resenyas
from utils_extraccion.sesion import get_pending_games, ask_overwrite_file, overwrite_confirmation, update_config

def _download_game_data(game, curr_idx, sesion):
    """
    Guarda en el campo "reviews" de game las reseñas disponibles del juego

    Args:
        game (dict): Diccionario con la información de un juego
        curr_idx (int): Indice del progreso de la extraccion
        sesion(session.Requests): Sesion de requests
    Returns:
        None
    """
    # Obtiene la info de un juego
    game["reviews"] = get_resenyas(game["id"], sesion, curr_idx < 100)

def D_informacion_resenyas(minio):
    try:
        # por si da un error en get_pending_games, evitar un UnboundLocalError en el finally
        start_idx, curr_idx, end_idx = -1,-1,-1

        pending_games, start_idx, curr_idx, end_idx = get_pending_games("D", minio)
        
        if not pending_games:
            print(f"No hay juegos en el rango [{curr_idx}, {end_idx}]")
            return
        
        # Si existe fichero preguntar si sobreescribir o insertar al final, 
        # esta segunda opción no controla duplicados
        if file_exists(steam_reviews_file, minio):
            origin = " en MinIO" if minio["minio_read"] else ""
            message = f"El fichero de reseñas ya existe{origin}:\n\n1. Añadir contenido al fichero existente\n2. Sobreescribir fichero\n\nIntroduce elección: "
            overwrite_file = ask_overwrite_file(message)
            if overwrite_file:
                # asegurarse de que se quiere eliminar toda la información
                if overwrite_confirmation():
                    erase_file(steam_reviews_file, minio)
                else:
                    print("Operación cancelada")
                    return
                
        # El objeto de la sesión mejora el rendimiento cuando se hacen muchas requests a un mismo host
        sesion = requests.Session()
        user_agent = choice(user_agents)
        sesion.headers.update({'User-Agent': user_agent})
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