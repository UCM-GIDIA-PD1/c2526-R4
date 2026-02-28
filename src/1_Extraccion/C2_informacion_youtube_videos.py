import os
import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tqdm import tqdm

from src.utils.files import erase_file, file_exists, write_to_file
from src.utils.config import yt_statslist_file
from src.utils.minio_server import upload_to_minio

from utils_extraccion.sesion import get_pending_games, overwrite_confirmation, tratar_existe_fichero, update_config


'''
Script que almacena las estadísticas relativas a cada vídeo.

Requisitos:
- Módulo 'googleapiclient' para usar la API de youtube

Entrada:
- Necesita para su ejecución el archivo info_steam_youtube.json.gz y su información en el config.json

Salida:
- Los datos se almacenan en la carpeta data/ en formato JSONL comprimido.
'''

def _get_apikey():
    '''
    Devuelve la API KEY de Youtube de las variables del sistema
    '''
    # Cargamos la API KEY del sistema
    key = os.environ.get('API_KEY_YT')
    assert key, "La API_KEY no ha sido cargada"
    return key


def _process_game(youtube_service, video_id_list):
    ''' 
    Dada la build de cliente de la API de Youtube y un diccionario de ids de vídeos, devuelve una lista con el resultado del 
    request de las estadísticas de esos vídeos (Solo se añaden los vídeos categorizados como gaming)

    Args:
        - youtube_service (youtube api build): Build de la API de youtube
        - video_id_list (dict): Diccionario que contiene una lista de ids de videos

    Returns:
        list: Lista con la información de las estadísticas de los vídeos (viewCount, likeCount, favoriteCount, commentCount)
    '''
    # Si el juego no tiene videos, no se procesa
    if not video_id_list:
        return []
    
    # Transformamos la lista diccionarios en un string con todos ids
    ids_videos = [ video_id.get('id') for video_id in video_id_list]
    ids_string = ','.join(ids_videos)

    # Solicitud que gasta 1 unidad de cuota
    videos_request = youtube_service.videos().list(
        part="statistics,snippet",
        id=ids_string
    )
    videos_response = videos_request.execute()

    # Guardamos las estadísticas de los vídeos encontrados y las devolvemos
    stats_list = []
    for item in videos_response['items']:
        category = item['snippet'].get('categoryId')
        if str(category) == '20': # Comprobar que la categoría sea gaming, solo si es gaming se guarda 
            stats_list.append(
                {
                    'id' : item['id'],
                    'video_statistics' : item['statistics']    
                }
            )
    return stats_list


def C2_informacion_youtube_videos(minio):
    ''' 
    
    '''
    try:
        # Obtener información de la sesión
        start_idx, curr_idx, end_idx = -1,-1,-1
        pending_games, start_idx, curr_idx, end_idx = get_pending_games("C2", minio)

        # Si al obtener información de la sesión no hay juegos dentro del rango, acaba la ejecución
        if not pending_games:
            print(f"No hay juegos en el rango [{curr_idx}, {end_idx}]")
            return
        
        # Si existe fichero preguntar si sobreescribir o insertar al final, esta segunda opción no controla duplicados
        if file_exists(yt_statslist_file, minio):
            origen = " en MinIO" if minio["minio_read"] else ""
            mensaje = f"El fichero de información de YouTube ya existe{origen}:\n\n1. Añadir contenido al fichero existente\n2. Sobreescribir fichero\n\nIntroduce elección: "
            overwrite_file = tratar_existe_fichero(mensaje)
            if overwrite_file:
                # asegurarse de que se quiere eliminar toda la información
                if overwrite_confirmation():
                    erase_file(yt_statslist_file, minio)
                else:
                    print("Operación cancelada")
                    return
                
        API_KEY = _get_apikey()
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        print('Comenzando requests a la API de Youtube...\n')
        with tqdm(pending_games, unit="juegos") as pbar:
            for app in pbar:
                appid = app.get('id')
                pbar.set_description(f"Procesando appid {appid}")

                nombre = app.get("name")
                video_id_list = app.get('video_statistics')

                jsonl = {
                    'id' : appid,
                    'name' : nombre,
                    'video_statistics' : []
                }

                # Obtenemos información del juego solo si la lista no está vacía
                if video_id_list:
                    pbar.write(f"{nombre}")
                    jsonl['video_statistics'] = _process_game(youtube, video_id_list)

                curr_idx += 1
                # Escribimos en el archivo destino
                write_to_file(jsonl, yt_statslist_file)

    except KeyboardInterrupt:
        print("\n\nDetenido por el usuario. Guardando antes de salir...")
    except HttpError as e:
        error_content = json.loads(e.content.decode("utf-8"))
        reason = error_content["error"]["errors"][0]["reason"]

        if reason in ("quotaExceeded", "dailyLimitExceeded"):
            print("Límite de cuota de YouTube alcanzado")
        else:
            print(f"Error de YouTube API: {reason}")
    finally:
        if minio["minio_write"]: 
            corrrectly_uploaded = upload_to_minio(yt_statslist_file)
            if corrrectly_uploaded: erase_file(yt_statslist_file)

        gamelist_info = {"start_idx" : start_idx, "curr_idx" : curr_idx, "end_idx" : end_idx}
        if curr_idx > end_idx:
            print("Rango completado")
        update_config("C2", gamelist_info)



if __name__ == "__main__":
    C2_informacion_youtube_videos()