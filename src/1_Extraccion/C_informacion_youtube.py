import os
from googleapiclient.discovery import build
import Z_funciones

'''
Código que busca a partir de info_steam_games.json los juegos en YouTube, filtrando
por popularidad, antes de una fecha determinada e itera por los resultados (los 
vídeos), extrayendo sus estadísticas.

Información:
- Tenemos un límite por día de 10000 unidades para usar en la API de YouTube, de los cuales
99900 se irán en búsquedas, y otros 99 en hacer consultas de vídeos, dejando sin usar solo 
1 unidad.

Requisitos:
- Módulo `googleapiclient` para solicitar acceso a las API de YouTube de Python 
    (`pip install google-api-python-client`).
- Tener la API de YouTube de desarrollador.

Entrada:
- Necesita para su ejecución el archivo info_steam_games.json.

Salida:
- Los datos se almacenan en la el directorio indicado.
'''

def convertir_fecha_steam(fecha_str):
    """
    Convierte 'DD Mon, YYYY' -> 'YYYY-MM-DDT00:00:00Z'

    Args:
        fecha_str (str): Fecha en formato 'DD Mon, YYYY'.

    Returns:
        str | None: La fecha en formato RFC 3339 ('YYYY-MM-DDT00:00:00Z')
        Retorna None si la fecha no se carga correctamente.
    """
    if not fecha_str:
        return None

    try:
        # Para pasar de formato mes -> mes_num
        meses = {
            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06',
            'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
        }

        # Dividimos el string en partes
        limpia = fecha_str.replace(',', '')
        partes = limpia.split()

        # Nos aseguramos de que partes tenga longitud 3
        if len(partes) != 3:
            return None

        # Pasamos a formato numérico
        dia, mes_texto, anio = partes[0], partes[1], partes[2]
        dia = dia.zfill(2)
        mes_numero = meses.get(mes_texto)
        
        if not mes_numero:
            return None

        # Devolvemos en el formato necesario
        return f"{anio}-{mes_numero}-{dia}T00:00:00Z"

    except Exception as e:
        print(f"Error convirtiendo fecha '{fecha_str}': {e}")
        return None

def procesar_juego(youtube_service, nombre_juego, fecha_limite):
    """
    Devuelve una lista con las estadisticas de los 10 videos mas vistos de un juego 
    antes de su lanzamiento.

    Args:
        youtube_service (googleapiclient.discovery.Resource): Objeto de servicio de Google API 
            construido con la función build.
        nombre_juego (str): Título del videojuego para filtrar la búsqueda en YouTube.
        fecha_limite (str): Fecha en formato RFC 3339 que define el límite temporal superior de los vídeos.
        id_juego (int): Identificador único del juego para indexar las estadísticas.

    Returns:
        list[dict]: Una lista de diccionarios, donde cada uno contiene el id del juego 
        y las estadísticas (vistas, likes, etc.) del vídeo encontrado. Retorna una 
        lista vacía si ocurre un error o no hay resultados.
    """
    try:
        FECHA_INICIO_YOUTUBE = "2005-04-23T00:00:00Z"
        # Si la fecha de salida del juego es anterior a Youtube, devuelve None
        if fecha_limite < FECHA_INICIO_YOUTUBE:
            print("El juego es anterior a YouTube")
            return

        # Solicitud que gasta 100 unidades de cuota
        search_request = youtube_service.search().list(
            part="id",
            q=f'intitle:"{nombre_juego}"',
            order="viewCount",
            publishedBefore=fecha_limite,
            type="video",
            maxResults=10, # Limitado a 10 vídeos por búsqueda
            safeSearch='none',
            videoCategoryId="20" # Categoría de vídeo Gaming
        )
        search_response = search_request.execute()
        if not search_response.get('items'):
            print("No se encontraron videos")
            return []
        
        # Guardamos las ids de los vídeos
        ids_videos = [item['id']['videoId'] for item in search_response.get('items')]
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
        print(f"Error buscando '{nombre_juego}': {e}")
        return []

def main():
    # Cargamos la API del sistema
    API_KEY = os.environ.get('API_KEY_YT')
    if not API_KEY:
        print('La API_KEY no ha sido cargada')
        return

    # Cargamos los datos del JSON que contiene las fechas para hacer las búsqueda correctamente
    ruta_json = r'data\info_steam_games.json'
    juegos = Z_funciones.cargar_datos_locales(ruta_json)

    if not juegos:
        print('Error al cargar los juegos')
        return
    print('Buscando juegos en YouTube...\n')

    # Creamos el googleapiclient.discovery.Resource
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    print("oiahfiashfioeashf")
    # Iteramos los juegos
    lista_juegos = juegos.get("data")
    contador = 0
    for juego in lista_juegos:
        nombre = juego.get('appdetails').get("name")
        fecha = juego.get('appdetails').get("release_date").get("date")
        fecha_formateada = convertir_fecha_steam(fecha)

        if nombre and fecha_formateada:
            print(f"{nombre}: {fecha}")
            juego['video_statistics'] = procesar_juego(youtube, nombre, fecha_formateada)
        else:
            print(f'Juego con entrada incompleta: {nombre}')
        
        contador += 1
        if contador == 99:
            break

    Z_funciones.guardar_datos_dict(lista_juegos, r"data\info_steam_games_and_youtube.json")

if __name__ == "__main__":
    main()