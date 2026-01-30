import os
from googleapiclient.discovery import build # pip install google-api-python-client
from dotenv import load_dotenv
import json
from datetime import datetime
import Z_funciones

'''
Este script puede cargar las estadisticas de los 10 videos mas vistos de los juegos indicados por un json y genera un nuevo
json que contiene una lista con las estadisticas de cada video. 

Requisitos:
- Módulo `googleapiclient` para solicitar acceso a las API de YouTube de Python.
- Módulo `dotenv`.

Entrada:
- Necesita para su ejecución el archivo info_steam_games.json.

Salida:
- Los datos se almacenan en la el directorio indicado.
'''

def convertir_fecha_steam(fecha_str):
    """
    Convierte '21 Aug, 2012' -> '2012-08-21T00:00:00Z'
    """

    if not fecha_str:
        return None
        
    meses = {
        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06',
        'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
    }

    try:
        limpia = fecha_str.replace(',', '')
        
        partes = limpia.split()
        
        if len(partes) != 3:
            return None

        dia, mes_texto, anio = partes[0], partes[1], partes[2]

        dia = dia.zfill(2)

        mes_numero = meses.get(mes_texto)
        
        if not mes_numero:
            return None

        return f"{anio}-{mes_numero}-{dia}T00:00:00Z"

    except Exception as e:
        print(f"Error convirtiendo fecha '{fecha_str}': {e}")
        return None

def procesar_juego(youtube_service, nombre_juego, fecha_limite, id_juego):
    # Devuelve una lista con las estadisticas de los 10 videos mas vistos de un juego antes de su lanzamiento
    try:
        search_request = youtube_service.search().list(
            part="id",
            q=f'intitle:"{nombre_juego}"',
            order="viewCount",
            publishedBefore=fecha_limite,
            type="video",
            maxResults=10,
            safeSearch='none',
            videoCategoryId="20"
        ) # Esto son 100 unidades de cuota
        search_response = search_request.execute()

        if not search_response.get('items'):
            print("No se encontraron videos")
            return []
        
        ids_videos = [item['id']['videoId'] for item in search_response.get('items')]

        ids_string = ','.join(ids_videos)

        videos_request = youtube_service.videos().list(
            part="statistics",
            id=ids_string
        ) # Esto es 1 unidad de cuota
        videos_response = videos_request.execute()

        lista_estadisticas = []

        for item in videos_response['items']:
            stats = {'id': id_juego, 'statistics': item['statistics']}
            lista_estadisticas.append(stats)
        
        return lista_estadisticas
        

    except Exception as e:
        print(f"Error buscando '{nombre_juego}': {e}")
        return []

def main():
    API_KEY = os.environ.get('API_KEY_YT')
    ruta_json = r'' #MODIFICAR A DONDE SE TENGA EL FICHERO JSON

    if not API_KEY:
        print('API_KEY NO ENCONTRADA')
        return

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