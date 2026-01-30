import os
from googleapiclient.discovery import build # pip install google-api-python-client
import Z_funciones

'''
Este script puede cargar las estadisticas de los 10 videos mas vistos de los juegos indicados por un json y genera un nuevo
json que contiene una lista con las estadisticas de cada video.

Información:
- Tenemos un límite por día de 10000 unidades para usar en la API de YouTube, de los cuales
99900 se irán en búsquedas, y otros 99 en hacer consultas de vídeos, dejando sin usar solo 
1 unidad.

Requisitos:
- Módulo `googleapiclient` para solicitar acceso a las API de YouTube de Python.

Entrada:
- Necesita para su ejecución el archivo info_steam_games.json.

Salida:
- Los datos se almacenan en la el directorio indicado.
'''

def convertir_fecha_steam(fecha_str):
    """
    Convierte 'DD Mon, YYYY' -> 'YYYY-MM-DDT00:00:00Z'
    """

    if not fecha_str:
        return None
    
    # Para pasar de formato mes -> mes_num
    meses = {
        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06',
        'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
    }

    try:
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

def procesar_juego(youtube_service, nombre_juego, fecha_limite, id_juego):
    """
    Devuelve una lista con las estadisticas de los 10 videos mas vistos de 
    un juego antes de su lanzamiento.
    
    youtube_service: Objeto de servicio de Google API construido con la función build.
    nombre_juego: String con el título del videojuego para filtrar la búsqueda en YouTube.
    fecha_limite: String en formato RFC 3339 que define el límite temporal superior de los vídeos.
    id_juego: Identificador numérico o string único del juego para indexar las estadísticas.
    """

    try:
        # Solicitud que gasta 100 unidades de cuota
        search_request = youtube_service.search().list(
            part="id",
            q=f'intitle:"{nombre_juego}"',
            order="viewCount",
            publishedBefore=fecha_limite,
            type="video",
            maxResults=10,
            safeSearch='none',
            videoCategoryId="20"
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
            stats = {'id': id_juego, 'statistics': item['statistics']}
            lista_estadisticas.append(stats)
        return lista_estadisticas

    except Exception as e:
        print(f"Error buscando '{nombre_juego}': {e}")
        return []

def main():
    # Encontramos la API del sistema
    API_KEY = os.environ.get('API_KEY_YT')
    if not API_KEY:
        print('API_KEY NO ENCONTRADA')
        return

    # Cargamos los datos del JSON que contiene las fechas para hacer las búsqueda 
    # correctamente
    ruta_json = r'data\info_steam_games.json'
    juegos = Z_funciones.cargar_datos_locales(ruta_json)

    if juegos:
        print('Juegos cargados correctamente')

        youtube = build('youtube', 'v3', developerKey=API_KEY)

        '''
        for juego in juegos:

            nombre = juego.get('nombre')
            fecha = juego.get('fecha')
            id = juego.get('id')

            if nombre and fecha:
                stats = procesar_juego(youtube, nombre, fecha, id)
                juego['video_statistics'] = stats
            else:
                print(f'Entrada incompleta: {juego}')
        '''

        nombre = 'Counter-Strike 2'
        fecha = convertir_fecha_steam('21 Aug, 2012')
        id = 730

        if nombre and fecha:
            stats = procesar_juego(youtube, nombre, fecha, id)
            #juego['video_statistics'] = stats
            print(stats)
        else:
            #print(f'Entrada incompleta: {juego}')
            print('no')

        #with open("steam_apps_with_stats.json", "w", encoding = "utf-8") as f:
            #json.dump(juegos, f, ensure_ascii = False, indent = 2)

if __name__ == "__main__":
    main()