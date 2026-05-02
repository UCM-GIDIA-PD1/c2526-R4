"""
Extraer los nuevos datos bajo un prefijo específico.
Al final del proceso integrarlos con los datos anteriores.
    - Subir a MinIO con tag de versiones?
    - Metadatos de extracción: fecha, cantidad de registros, etc.?

1. Extraer los nuevos appids
2. Extraer información de steam (appdetails y appreviewhistogram)
3. Extraer información de las imágenes de Steam
4. Extraer reseñas de Steam (cuantas de cada juego?)
5. Extraer información de YouTube
6. Incorporar los nuevos datos a los anteriores

Problemas para el análisis del desempeño
- FASTopic
- Como hacemos para analizar el desempeño de los modelos con los nuevos datos?
- Previsión de problema: Para nuestra lista actual de appids hay muchísimos juegos filtrados por coming soon, con este método no los volvemos a incluir,
probablemente todos los appids nuevos sean coming soon, vamos a tener muy pocos datos nuevos.
- Nuestro pipeline actual tiene un problema fundamental y es que filtramos en la etapa de extracción, lo que hace que no podamos volver a incluir los 
juegos que antes estaban filtrados. Deberíamos extraer toda la información de todos los appids y luego filtrar en la etapa de transformación, así podríamos 
incluir los nuevos appids aunque sean coming soon.

Propuesta para cambiar el pipeline:
- Extraer TODA la información de los appids, sin filtrar nada
- No extraer todo Steam, creo que es suficiente hacer un random sampling de por ejemplo 40K appids. Ya en cada modelo ver de esos 40K cuantos se pueden usar
- Luego en la etapa de transformación, aplicar el filtro de coming soon y otros filtros

Secundario:
- Modificar integración con MinIO, de creo que solo files.py debería saber de MinIO
- Para escritura puede que se pueda diseñar interfaz para decidir qué ficheros locales sincronizar con MinIO
- Añadir un modelo más de reviews, BERT
- Diseñar un mejor sistema de nombres de ficheros
- Estamos usando clases para los modelos???

Ya en general, quitar complejidad innecesaria y un codigo más legible y sencillo 
"""

from src.A_Extraccion.utils_extraccion.steam_requests import get_appids
from src.A_Extraccion.B_informacion_juegos import _download_game_data
from utils.files import read_file, write_to_file
from tqdm import tqdm
from time import sleep, time
from numpy.random import uniform
from requests import Session
from torch import nn
from sentence_transformers import SentenceTransformer
import torchvision.models as models
import torchvision.transforms as transforms
from src.A_Extraccion.E_metadatos_imagenes import _analiza_imagen
from src.A_Extraccion.utils_extraccion.steam_requests import get_resenyas
from src.A_Extraccion.C1_informacion_youtube_busquedas import _IP_interval_rotation
from src.A_Extraccion.utils_extraccion.webscraping import start_tor, renew_tor_ip, new_configured_chromium_page, search_youtube
from src.A_Extraccion.C2_informacion_youtube_videos import _get_apikey, _request_youtube
from googleapiclient.discovery import build
import pandas as pd
from src.B_Transformacion.B_games_info_transformacion import trans_prices, trans_popularity
from src.B_Transformacion.C_estadisticas_youtube import _transform_to_dataframe, procesar_impacto_youtube
from src.B_Transformacion.filtrado_youtube_llm import filtrado_por_clasificacion
from src.utils.config import yt_stats_parquet_file
from src.utils.config import appidlist_file, gamelist_file, youtube_scraping_file, yt_statslist_file, steam_reviews_file, banners_file
from src.B_Transformacion.E_info_imagenes_transformacion import reduct_dataframes_from_models
from src.utils.config import P_banners_file
from src.B_Transformacion.D2_limpieza_reviews import limpieza_inicial, detect_language, limpieza_final, to_dataframe
from src.utils.config import steam_reviews_parquet_file
# Extraer los nuevos de appids

def extract_new_appids():
    """
    Requisitos ((*)sujeto a cambios):
    - variable de entorno STEAM_API_KEY
    - * fichero appids_list.json.gz para saber el último appid extraído
    """
    appid_list = read_file(appidlist_file)        
    last_appid = appid_list[-1]
    new_appids = get_appids(last_appid=last_appid)
    write_to_file(new_appids, "new_appid_list.json.gz")
    return new_appids

def extract_new_appids_v2():
    """
    Requisitos ((*)sujeto a cambios):
    - variable de entorno STEAM_API_KEY
    - * fichero appids_list.json.gz para saber el último appid extraído
    """
    get_appids
    gamesinfo = read_file(gamelist_file)
    old_appids = set(game.get("id") for game in gamesinfo)
    new_appids = get_appids(last_appid=0)
    new_appids = [appid for appid in new_appids if appid not in old_appids]
    write_to_file(new_appids, "new_appid_list.json.gz")
    return new_appids

# Extraer la información de Steam de los nuevos appids
def extract_steam_info(new_appids, session):
    
    with tqdm(new_appids, unit = "appids") as pbar:
        for appid in pbar:
            pbar.set_description(f"Procesando appid {appid}")
            try:
                desc = _download_game_data(appid, session)
                write_to_file(desc, "new_gamelist.jsonl.gz")
            except Exception as e:
                pbar.write(str(e))
            finally:
                curr_idx += 1
                wait = uniform(1.7, 2.5)
                sleep(wait)
    return "new_gamelist.jsonl.gz"

def _load_image_models():
    # Resnet, entrenado para reconocer formas
    model_resnet = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model_resnet = nn.Sequential(*(list(model_resnet.children())[:-1]))
    model_resnet.eval()

    # ConvNeXt, optimizado para texturas y detalles finos
    model_convnext = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.DEFAULT)
    model_convnext.classifier = nn.Identity() # Quitamos la capa de clasificación
    model_convnext.eval()

    # Clip, modelo de OpenAI que reconoce conceptos semánticos, estilos y estética
    model_clip = SentenceTransformer('clip-ViT-B-32')
    model_clip.eval()

    # Definimos las trasnformaciones que vamos a hacer a cada imagen (para poder meterlas en el modelo)
    trans = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    return model_resnet, model_convnext, model_clip, trans

# Extraer la información de las imágenes de Steam de los nuevos appids
def extract_steam_images(apps_info, session):
    model_resnet, model_convnext, model_clip, trans = _load_image_models()
    ruta_imagenes = "new_images/"
    with tqdm(apps_info, unit="juegos") as pbar:
        for juego in pbar:
            appid = juego.get("id")
            pbar.set_description(f"Procesando appid: {appid}")
            
            url = juego.get("appdetails", {}).get("header_url")
            if not url:
                raise ValueError(f"No se encontró URL de imagen para el juego {appid}")
            download_images = True
            try:
                caracteristicas = _analiza_imagen(ruta_imagenes, url, trans, appid, download_images, model_resnet, model_clip, model_convnext, session)

                resultado_juego = {
                    "id": appid,
                    "brillo": caracteristicas["brillo_medio"],
                    "v_resnet": caracteristicas["vector_resnet"],
                    "v_convnext": caracteristicas["vector_convnext"],
                    "v_clip": caracteristicas["vector_clip"]
                }

                write_to_file(resultado_juego, "new_info_imagenes.jsonl.gz")
                curr_idx += 1
                
                if download_images: 
                    sleep(uniform(0.1, 0.2))

            except Exception as e:
                pbar.write(f"Error procesando imagen del juego {appid}: {e}")
                curr_idx += 1
                continue
    pass

# Extraer las reseñas de Steam de los nuevos appids
def extract_steam_reviews(apps_info, session):
    with tqdm(apps_info, unit="juegos") as pbar:
        for juego in pbar:
            appid = juego.get("id")
            try:
                reviews = get_resenyas(appid, session, False)
                resultado_juego = {
                    "index" : 67, # es una variable residual que no se usa para nada
                    "id": appid,
                    "name" : juego.get("appdetails", {}).get("name"),
                    "total_reviews": juego.get("appreviewhistogram", {}).get("rollups", {}).get("total_recommendations"),
                    "reviews": reviews
                }
                write_to_file(resultado_juego, "new_reviews.jsonl.gz")
            except Exception as e:
                pbar.write(f"Error obteniendo reseñas para el juego {appid}: {e}")
    pass

# Extraer la información de YouTube de los nuevos appids
def extract_youtube_info_1(apps_info, session):
    start_tor()
    session = new_configured_chromium_page()
    last_timestamp = time()
    interval = _IP_interval_rotation()
    with tqdm(apps_info, unit="juegos") as pbar:
            for game in pbar:
                # Cargamos los datos
                appid = game.get('id')
                name = game.get('appdetails').get("name")
                date = game.get('appdetails').get("release_date")
                pbar.set_description(f"Procesando appid {appid}")

                # Si se han cargado los datos correctamente, hacemos búsqueda en YouTube
                if name and date:
                    id_list = search_youtube(name, date, session)
                    if id_list == []:
                        tqdm.write(f'Juego sin vídeos o error al buscarlo: {name}')
                    jsonl = {'id':appid,'name':name,'video_statistics':id_list}
                    write_to_file(jsonl, "new_info_steam_youtube.jsonl.gz")
                    session.wait(4, scope=0.4) # Espera aleatoria de entre 2.4 y 5.6 segundos
                else:
                    tqdm.write(f'Juego con entrada incompleta: {name}')
                current_time = time()
                if current_time - last_timestamp >= interval:
                    last_timestamp = current_time
                    interval = _IP_interval_rotation()
                    session = renew_tor_ip(session)
                    if not session:
                        break
    return "new_info_steam_youtube.jsonl.gz"

def extract_youtube_info_2(apps_info):
    API_KEY = _get_apikey()
    youtube = build('youtube', 'v3', developerKey=API_KEY)

    with tqdm(apps_info, unit="juegos") as pbar:
        for app in pbar:
            jsonl = None
            try:
                appid = app.get('id')
                name = app.get('appdetails').get("name")
                pbar.set_description(f"Procesando appid {appid}")
                video_id_list = app.get('video_id_list', [])
                if video_id_list == []:
                    tqdm.write(f'Juego sin vídeos o error al buscarlo: {name}')
                jsonl = {
                    'id' : appid,
                    'name' : name,
                    'video_statistics' : []
                }
                # Obtenemos información del juego solo si la lista no está vacía
                if video_id_list:
                    jsonl['video_statistics'] = _request_youtube(youtube, video_id_list)

                write_to_file(jsonl, "new_youtube_statistics.jsonl.gz")
            except Exception as e:
                pbar.write(f"Error obteniendo información de YouTube para el juego {appid}: {e}")
    return "new_youtube_statistics.jsonl.gz"

def b_transformacion(gamelist_path, minio_cfg={"minio_write": False, "minio_read": False}):
    """
    Transforma la información técnica de Steam para los dos problemas (Precio y Popularidad).
    Usa las funciones originales para asegurar consistencia en los nombres de las columnas.
    """
    print("Iniciando B_Transformación...")
    

    data = read_file(gamelist_path, minio_cfg)
    if not data:
        print("No se encontraron datos para transformar.")
        return
    
    df_full = pd.DataFrame(data)

    print("Generando Parquet de Popularidad...")
    df_pop = trans_popularity(df_full.copy(), minio_cfg)
    df_pop.to_parquet("new_games_info_popularity.parquet")

    print("Generando Parquet de Precios...")
    df_prices = trans_prices(df_full.copy(), minio_cfg)
    df_prices.to_parquet("new_games_info_prices.parquet")
    
    print(f"B_Transformación completada.")
    print(f"Archivos guardados en:\n - \"new_games_info_popularity.parquet\"\n - \"new_games_info_prices.parquet\"")

def c_transformacion_youtube(youtube_stats_path, minio_cfg={"minio_write": False, "minio_read": False}):
    """
    Filtra los vídeos mediante LLM, aplana las estadísticas y calcula el yt_score final.
    Mantiene la estructura de columnas exacta para el merge posterior.
    """
    print("Iniciando C_Transformación YouTube...")
    

    data = read_file(youtube_stats_path, minio_cfg)
    if not data:
        print("No se encontraron datos de YouTube para procesar.")
        return


    print("Filtrando vídeos con LLM para eliminar ruido...")
    data_filtrado = filtrado_por_clasificacion(data, minio_cfg)
    

    print("Transformando a DataFrame y aplanando estadísticas...")
    df = _transform_to_dataframe(data_filtrado)


    print("Calculando métrica yt_score...")
    df_metrica = procesar_impacto_youtube(df)


    print(f"Guardando Parquet en: \"new_yt_stats.parquet\"")
    df_metrica.to_parquet("new_yt_stats.parquet")
    
    print("C_Transformación YouTube completada.")



def integrate_new_data():

    pass

if __name__ == "__main__":
    session = Session()
    new_appids = extract_new_appids()
    new_gameinfo_file = extract_steam_info(new_appids, session)

    apps_info = read_file(new_gameinfo_file)
    extract_steam_images(apps_info, session)
    extract_steam_reviews(apps_info, session)

    new_youtube_info_file = extract_youtube_info_1(apps_info, session)
    youtube_info_1 = read_file(new_youtube_info_file)
    youtube_info_2 = extract_youtube_info_2(youtube_info_1, session)
    b_transformacion(new_gameinfo_file)
    c_transformacion_youtube(youtube_info_2)
    