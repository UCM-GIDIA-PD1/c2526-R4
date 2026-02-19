import os
from googleapiclient.discovery import build
import utils
from utils.config import videoid_list_file, yt_statslist_file
from utils.files import log_appid_errors, read_file, write_to_file
from tqdm import tqdm
from googleapiclient.errors import HttpError

'''
Segunda parte de la extracción de YouTube: videos.

Habiendo ya sacado la información de las búsquedas, este script busca las estadísticas relativas
a los vídeos de cada juego buscado, mediante la API de YouTube.

Información:
- Tenemos un límite por día de 10000 unidades para usar en la API de YouTube, por lo que podemos sacar
    la información de 10000 juegos por día.

Requisitos:
- Módulo `googleapiclient` para solicitar acceso a las API de YouTube de Python 
    (`pip install google-api-python-client`).
- Tener la API de YouTube de desarrollador.

Entrada:
- Necesita para su ejecución el archivo info_steam_games_and_semiyoutube.json.gz.

Salida:
- Los datos se almacenan en la el directorio indicado.
'''

def process_game(youtube_service, video_id_list, id_juego):
    """
    Dado un array que contiene diccionarios conlos ids de los videos de un juego, obtiene las estadísticas de todos los videos 
    devolviendo una lista de video_statistics.

    Args:
        youtube_service (googleapiclient.discovery.Resource): Objeto de servicio de Google API 
            construido con la función build.
        video_id_list (list): Lista que contiene un diccionario con los ids de los videos de un juego
        id_juego (str): Id del juego 

    Returns:
        list[dict]: Una lista de diccionarios, donde cada uno contiene el id del juego 
        y las estadísticas (vistas, likes, etc.) del vídeo encontrado. Retorna una 
        lista vacía si ocurre un error o no hay resultados.
    """
        
    # Si el juego no tiene videos, no se procesa
    if not video_id_list:
        return []
    
    # Transformamos la lista diccionarios en un string con todos ids
    ids_videos = [ video_id.get('id') for video_id in video_id_list]
    ids_string = ','.join(ids_videos)

    # Solicitud que gasta 1 unidad de cuota
    videos_request = youtube_service.videos().list(
        part="statistics",
        id=ids_string
    )
    videos_response = videos_request.execute()

    # Guardamos las estadísticas de los vídeos encontrados y las devolvemos
    lista_estadisticas = []
    for item in videos_response['items']:
        lista_estadisticas.append(item)
    return lista_estadisticas


''' 
TODO: Implementar un config de C2, este config almacena el último appid procesado, la cantidad de juegos totales por procesar y
la cantidad de juegos procesados.
'''
def C2_informacion_youtube_videos():
    # Cargamos la API KEY del sistema
    API_KEY = os.environ.get('API_KEY_YT')
    assert API_KEY, "La API_KEY no ha sido cargada"

    # Cargamos la lista de juegos
    appidlist = read_file(videoid_list_file)
    assert appidlist, "No se ha podido leer el archivo de lista de videos"

    # Cargamos la lista de juegos a procesar
    datalist = appidlist.get('data')

    # Creamos el googleapiclient.discovery.Resource
    youtube = build('youtube', 'v3', developerKey=API_KEY)

    info = {}
    info['data'] = []
    print("Initiating video statistics request...\n")
    with tqdm(datalist, unit = "appids") as pbar:
        for app in pbar:
            appid = app.get('id')
            pbar.set_description(f"Procesando appid: {appid}")
            try:
                nombre = app.get("name")
                id_juego = app.get('id')
                video_id_list = app.get('video_statistics')

                # Si la lista está vacía no se procesa el juego
                if video_id_list:
                    print(f"{nombre}")
                    stats = {
                        'id' : id_juego,
                        'name' : nombre,
                        'video_statistics' : process_game(youtube, video_id_list, id_juego)
                    }
                    info['data'].append(stats)
            except HttpError as e:
                if e.resp.status == 403:
                    pbar.write("Límite de cuota de YouTube alcanzado. Abortando proceso.")
                    log_appid_errors("Quota exceeded (403)")
                    write_to_file(info, yt_statslist_file)
                    raise  # 🔥 se relanza para parar TODO
                else:
                    pbar.write(str(e))
                    log_appid_errors(str(e))
            finally:
                write_to_file(info, yt_statslist_file)


if __name__ == "__main__":
    C2_informacion_youtube_videos()