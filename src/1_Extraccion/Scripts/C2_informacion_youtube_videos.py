import os
from googleapiclient.discovery import build
import Z_funciones
from Z_funciones import proyect_root

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

def procesar_juego(youtube_service, video_id_list, id_juego):
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
    try:
        
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

    except Exception as e:
        print(f"Error buscando '{id_juego}': {e}")
        return []

def C2_informacion_youtube_videos():
    # Cargamos la API del sistema
    API_KEY = 'AIzaSyCJuw9OLbCctEuFRNVakm4eTabLORRlBUM'#os.environ.get('API_KEY_YT')
    assert API_KEY, "La API_KEY no ha sido cargada"

    # Cargamos los datos del JSON que contiene los VIDEO ID de cada juego
    ruta_json = proyect_root() / "data" / "info_steam_youtube_1_4.json.gz" # (CAMBIAR NOMBRE)
    juegos = Z_funciones.cargar_datos_locales(ruta_json)

    if not juegos:
        print('Error al cargar la lista de juegos')
        return
    
    print('Obteniendo estadísticas de los videos...\n')

    # Creamos el googleapiclient.discovery.Resource
    youtube = build('youtube', 'v3', developerKey=API_KEY)

    info_json = {}
    info_json['data'] = []

    # Iteramos los juegos
    lista_juegos = juegos.get("data")
    contador = 0
    for juego in lista_juegos:
        nombre = juego.get("name")
        id_juego = juego.get('id')
        video_id_list = juego.get('video_statistics')

        # Si la lista está vacía no se procesa el juego
        if video_id_list:
            print(f"{nombre}")
            info = {}
            info['id'] = id_juego
            info['name'] = nombre
            info['video_statistics'] = procesar_juego(youtube, video_id_list, id_juego)
            info_json['data'].append(info)
        else:
            print(f'El juego {id_juego} no tiene video_statistics')
        
        # Placeholder para solo obtener información de 100 juegos (CAMBIAR EN LA VERSIÓN FINAL) 
        contador += 1
        if contador == 99: 
            break


    data_dir = proyect_root() / "data"
    ruta_final_gzip = data_dir / 'info_steam_youtube.json.gz'
    Z_funciones.guardar_datos_dict(info_json, ruta_final_gzip)

if __name__ == "__main__":
    C2_informacion_youtube_videos()