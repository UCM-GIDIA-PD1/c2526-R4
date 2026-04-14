'''
Dado una lista de diccionarios, filtra los videos dentro de cada uno de ellos usando ollama (qwen2.5:3B)
Este fichero es usado como ayuda de C_estadisticas_youtube.py.
'''

import ollama
from src.utils.config import yt_statslist_file, raw_game_info_popularity
from src.utils.files import read_file, write_to_file
from tqdm import tqdm

MODELO = 'qwen2.5:3b'

def descargar_modelo():
    try:
        ollama.show(MODELO)
    except Exception:
        print(f"Descargando el modelo {MODELO}. Esto puede tardar unos minutos...")
        ollama.pull(MODELO)

def clasificacion_ollama(game_name, steam_description, video_title, views, channel):
    
    prompt = f"""
Act as a binary data classifier. Determine if the following YouTube video belongs to the content ecosystem of the video game '{game_name}'. The game is from Steam and the videos are already filtered by the gaming category.

Steam Data:
- Description: {steam_description}

Video Data:
- Title: {video_title}
- Views: {views}
- Channel: {channel}

Classification Rules:
1. Respond with 1 if the video is directly related to the video game (e.g., gameplays, reviews, official trailers, original soundtrack, lore, analysis, tournaments).
2. Respond with 0 if the video is NOT related to the video game, even if the title contains the keyword (e.g., other video games that are not the original one or that could be confused with it due to the title).
3. Return ONLY the number 1 or the number 0.
    """

    try:
        respuesta = ollama.chat(model=MODELO, messages=[
            {'role': 'user', 'content': prompt}
        ], options={'temperature': 0.0})
        
        return respuesta['message']['content'].strip()
    except Exception as e:
        return f"Error: {str(e)}"
    
def filtrado_por_clasificacion(data, minio):
    raw_steam_info = read_file(raw_game_info_popularity, minio)
    dict_id_description = {str(item["id"]): {"short_description": item['appdetails'].get("short_description", "No description"), 
                                        "name": item['appdetails'].get("name", "No name")} 
                                        for item in raw_steam_info}
    data_filtrado = []
    
    descargar_modelo()

    print('Comenzando filtrado\n')
    try:
        with tqdm(data, unit = "juegos") as pbar:
            for juego in pbar:
                appid = str(juego['id'])
                pbar.set_description(f"Procesando appid {appid}")
                game_name = dict_id_description[appid]['name']
                game_filtered_info = {'id':int(appid), 'name':game_name, 'video_statistics':[]}
                short_description = dict_id_description[appid]['short_description']

                for video in juego['video_statistics']:
                    video_title = video.get('video_title', 'No title')
                    views = video.get('video_statistics', {}).get('viewCount', 0)
                    channel = video.get('channel', 'No channel')
                    if clasificacion_ollama(game_name, short_description, video_title, views, channel) == '1':
                        new_video_data = video.copy()
                        new_video_data.pop('video_title')
                        new_video_data.pop('channel')
                        game_filtered_info['video_statistics'].append(new_video_data)
                        tqdm.write(f'Aceptado:    Video de id {video['id']} del juego {game_name}')
                    else:
                        tqdm.write(f'Deshechado:  Video de id {video['id']} del juego {game_name}')
                data_filtrado.append(game_filtered_info)
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        return data_filtrado

if __name__ == '__main__':
    # Main para debuguear
    print('Obteniendo archivo')
    data = read_file(yt_statslist_file, {'minio_write':False, 'minio_read':True})
    assert data, 'No se ha podido leer el archivo'
    
    data_filtrado = filtrado_por_clasificacion(data, {'minio_write':False, 'minio_read':True})

    write_to_file(data_filtrado, 'data/test_youtube.json')