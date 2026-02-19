import requests
import Z_funciones
from random import uniform
import time
from tqdm import tqdm
from utils.steam_requests import get_resenyas
from utils.config import config_file

'''
Script que guarda la información procedente de appreviews

Requisitos:
Módulo requests para solicitar acceso a las APIs.

Entrada:
Necesita para su ejecución el archivo steam_apps.json

Salida:
Los datos se almacenan en la carpeta data/ en formato JSON.
'''

def download_game_data(id, sesion):
    # Obtiene la info de un juego
    game_info = {"id": id, "resenyas": []}
    game_info["resenyas"] = get_resenyas(id, sesion)

    return game_info

def D_informacion_resenyas(minio = False):
    # El objeto de la sesión mejora el rendimiento cuando se hacen muchas requests a un mismo host
    origin = "steam_apps.json.gz"
    final = "info_steam_resenyas.json.gz"
    juego_ini, juego_fin, juegos_pendientes, ruta_temp_jsonl, ruta_final_gzip, ruta_config = Z_funciones.abrir_sesion(origin, final, True, minio)
    if not juego_ini:
        return

    sesion = requests.Session()
    sesion.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

    idx_actual = juego_ini
    try:
        with tqdm(juegos_pendientes, unit = "appids") as pbar:
            for appid in pbar:
                try:
                    data = download_game_data(appid, sesion)
                    
                    if data != {}:
                        Z_funciones.guardar_datos_dict(data, ruta_temp_jsonl)
                        

                    # Pausa para respetar la API
                    wait = uniform(1.5, 2)
                    time.sleep(wait)

                except Exception as e:
                    # Si falla un juego específico, lo logueamos y seguimos con el siguiente
                    print(f"Error procesando juego {appid}: {e}")
                    continue
                idx_actual += 1

    except KeyboardInterrupt:
        print("\n\nDetenido por el usuario. Guardando antes de salir...")
    finally:
        Z_funciones.cerrar_sesion(ruta_temp_jsonl, ruta_final_gzip, ruta_config, idx_actual, juego_fin, minio)


if __name__ == "__main__":
    # Poner a True para traer y mandar los datos a MinIO
    D_informacion_resenyas(False)