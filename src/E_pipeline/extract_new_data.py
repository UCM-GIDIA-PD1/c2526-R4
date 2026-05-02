from src.A_Extraccion.utils_extraccion.steam_requests import get_appids
from src.A_Extraccion.B_informacion_juegos import _download_game_data
from src.utils.files import read_file, write_to_file
from tqdm import tqdm
from pathlib import Path
import os
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
from src.B_Transformacion.filtrado_youtube_llm import descargar_modelo, clasificacion_ollama
from src.utils.config import appidlist_file, gamelist_file
from src.B_Transformacion.E_info_imagenes_transformacion import reduct_dataframes_from_models
from src.B_Transformacion.D2_limpieza_reviews import limpieza_inicial, detect_language, limpieza_final, to_dataframe

def extract_new_appids():
    appid_list = read_file(appidlist_file)        
    last_appid = appid_list[-1]
    new_appids = get_appids(last_appid=last_appid)
    write_to_file(new_appids, Path("new_appid_list.json.gz"))
    return new_appids

def extract_new_appids_v2():
    gamesinfo = read_file(gamelist_file)
    old_appids = set(game.get("id") for game in gamesinfo)
    new_appids = get_appids(last_appid=0)
    new_appids = [appid for appid in new_appids if appid not in old_appids]
    write_to_file(new_appids, Path("new_appid_list.json.gz"))
    return new_appids

def extract_steam_info(new_appids, session):
    output_file = Path("new_gamelist.jsonl.gz")
    with tqdm(new_appids, unit = "appids") as pbar:
        for appid in pbar:
            pbar.set_description(f"Procesando appid {appid}")
            try:
                desc = _download_game_data(appid, session)
                write_to_file(desc, output_file)
            except Exception as e:
                pbar.write(f"Error en appid {appid}: {e}")
            finally:
                sleep(uniform(1.7, 2.5))
    return output_file

def _load_image_models():
    model_resnet = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model_resnet = nn.Sequential(*(list(model_resnet.children())[:-1]))
    model_resnet.eval()
    model_convnext = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.DEFAULT)
    model_convnext.classifier = nn.Identity()
    model_convnext.eval()
    model_clip = SentenceTransformer('clip-ViT-B-32')
    model_clip.eval()
    trans = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    return model_resnet, model_convnext, model_clip, trans

def extract_steam_images(apps_info, session):
    model_resnet, model_convnext, model_clip, trans = _load_image_models()
    ruta_imagenes = Path("new_images/")
    os.makedirs(ruta_imagenes, exist_ok=True)
    output_file = Path("new_info_imagenes.jsonl.gz")

    with tqdm(apps_info, unit="juegos") as pbar:
        for juego in pbar:
            appid = juego.get("id")
            pbar.set_description(f"Procesando imagen appid: {appid}")
            url = juego.get("appdetails", {}).get("header_url")
            if not url: continue
            try:
                caracteristicas = _analiza_imagen(ruta_imagenes, url, trans, appid, True, model_resnet, model_clip, model_convnext, session)
                resultado_juego = {
                    "id": appid,
                    "brillo": caracteristicas["brillo_medio"],
                    "v_resnet": caracteristicas["vector_resnet"],
                    "v_convnext": caracteristicas["vector_convnext"],
                    "v_clip": caracteristicas["vector_clip"]
                }
                write_to_file(resultado_juego, output_file)
                sleep(uniform(0.1, 0.2))
            except Exception as e:
                pbar.write(f"Error imagen {appid}: {e}")
    return output_file

def extract_steam_reviews(apps_info, session):
    output_file = Path("new_reviews.jsonl.gz")
    with tqdm(apps_info, unit="juegos") as pbar:
        for juego in pbar:
            appid = juego.get("id")
            try:
                reviews = get_resenyas(appid, session, False)
                resultado_juego = {
                    "id": appid,
                    "name" : juego.get("appdetails", {}).get("name"),
                    "reviews": reviews
                }
                write_to_file(resultado_juego, output_file)
            except Exception as e:
                pbar.write(f"Error reseñas {appid}: {e}")
    return output_file

def extract_youtube_info_1(apps_info):
    start_tor()
    session = new_configured_chromium_page()
    last_timestamp = time()
    interval = _IP_interval_rotation()
    output_file = Path("new_info_steam_youtube.jsonl.gz")
    with tqdm(apps_info, unit="juegos") as pbar:
        for game in pbar:
            appid = game.get('id')
            name = game.get('appdetails').get("name")
            date = game.get('appdetails').get("release_date")
            if name and date:
                id_list = search_youtube(name, date, session)
                jsonl = {'id':appid,'name':name,'video_statistics':id_list}
                write_to_file(jsonl, output_file)
                session.wait(4, scope=0.4)
            current_time = time()
            if current_time - last_timestamp >= interval:
                last_timestamp = current_time
                interval = _IP_interval_rotation()
                session = renew_tor_ip(session)
                if not session: break
    session.quit()
    return output_file

def extract_youtube_info_2(yt_search_data):
    API_KEY = _get_apikey()
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    output_file = Path("new_youtube_statistics.jsonl.gz")
    with tqdm(yt_search_data, unit="juegos") as pbar:
        for app in pbar:
            appid = app.get('id')
            name = app.get('name')
            video_id_list = app.get('video_statistics', [])
            jsonl = {'id' : appid, 'name' : name, 'video_statistics' : []}
            if video_id_list:
                try:
                    jsonl['video_statistics'] = _request_youtube(youtube, video_id_list)
                    write_to_file(jsonl, output_file)
                except Exception as e:
                    pbar.write(f"Error YT API {appid}: {e}")
    return output_file

def b_transformacion(gamelist_path):
    data = read_file(gamelist_path)
    df_full = pd.DataFrame(data)
    df_pop = trans_popularity(df_full.copy(), {"minio_write": False, "minio_read": False})
    df_pop.to_parquet(Path("new_games_info_popularity.parquet"))
    df_prices = trans_prices(df_full.copy(), {"minio_write": False, "minio_read": False})
    df_prices.to_parquet(Path("new_games_info_prices.parquet"))

def filtrado_por_clasificacion(data, minio):
    raw_steam_info = read_file(Path("new_gamelist.jsonl.gz"), minio)
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
def c_transformacion_youtube(youtube_stats_path):
    data = read_file(youtube_stats_path)
    data_filtrado = filtrado_por_clasificacion(data, {"minio_write": False, "minio_read": False})
    df = _transform_to_dataframe(data_filtrado)
    df_metrica = procesar_impacto_youtube(df)
    df_metrica.to_parquet(Path("new_yt_stats.parquet"))

def e_transformacion_imagenes(banners_raw_path):
    data = read_file(banners_raw_path)
    df = pd.DataFrame(data)
    reduct_dataframes_from_models(df)
    df.to_parquet(Path("new_P_info_imagenes.parquet"))

def d_transformacion_reviews(reviews_raw_path):
    raw_data = read_file(reviews_raw_path)
    df = to_dataframe(raw_data)
    df["text"] = df["text"].apply(limpieza_inicial)
    df["language"] = df["text"].apply(detect_language)
    df_en = df[df["language"] == "en"].copy()
    df_en["text"] = df_en["text"].apply(limpieza_final)
    df_en["weight"] = df_en["weight"].astype(float)
    df_en["appid"] = df_en["appid"].astype(str)
    df_en.drop(columns=["language"], inplace=True)
    df_en["language"] = "en" 
    df_en.to_parquet(Path("new_steam_reviews_processed.parquet"))

def crear_parquets_definitivos(pop_path, prices_path, images_path, youtube_path):
    print("Consolidando parquets definitivos...")
    df_B_pop = pd.read_parquet(pop_path)
    df_B_prices = pd.read_parquet(prices_path)
    df_E = pd.read_parquet(images_path)
    df_C = pd.read_parquet(youtube_path)

    for df in [df_B_pop, df_B_prices, df_E, df_C]:
        df["id"] = df["id"].astype(str)

    df_final_prices = pd.merge(df_B_prices, df_E, on="id").dropna()
    df_final_pop = pd.merge(df_B_pop, df_E, on="id")
    df_final_pop = pd.merge(df_final_pop, df_C, on="id").dropna()

    cols_faltantes = ['Shared/Split Screen', 'Steam Trading Cards', 'Remote Play Together']
    cols_sobrantes = ['pca_v_resnet_1', 'tsne_v_clip_1', 'Adjustable Difficulty', 'pca_v_resnet_2', 'Color Alternatives', 
                      'pca_v_clip_2', 'Mouse Only Option', 'tsne_v_convnext_2', 'Save Anytime', 'pca_v_convnext_2', 
                      'pca_v_convnext_1', 'tsne_v_clip_2', 'tsne_v_resnet_2', 'Keyboard Only Option', 'pca_v_clip_1', 
                      'tsne_v_resnet_1', 'Touch Only Option', 'tsne_v_convnext_1', 'Camera Comfort', 'Stereo Sound']
    
    for df_final in [df_final_prices, df_final_pop]:
        for col in cols_faltantes:
            if col not in df_final.columns:
                df_final[col] = 0
        
        cols_historial = [
            'num_juegos_previos_developers', 'num_juegos_previos_publishers',
            'ema_precio_developers', 'max_historico_precio_developers',
            'ema_reviews_developers', 'max_historico_reviews_developers'
        ]
        for col in cols_historial:
            if col in df_final.columns:
                df_final[col] = df_final[col].astype('float64')

        df_final.drop(columns=cols_sobrantes, inplace=True)

    df_final_prices.to_parquet(Path("final_dataset_prices.parquet"))
    df_final_pop.to_parquet(Path("final_dataset_popularity.parquet"))



if __name__ == "__main__":
    session = Session()
    
    #new_appids = extract_new_appids()
    #print("1/11")
    
    #new_gameinfo_file = extract_steam_info(new_appids, session)
    print("2/11")

    new_gameinfo_file = Path("new_gamelist.jsonl.gz")
    print(os.getcwd())
    apps_info = read_file(new_gameinfo_file)
    assert apps_info is not None
    #new_images_file = extract_steam_images(apps_info, session)
    new_images_file = Path("new_info_imagenes.jsonl.gz")
    #print("3/11")
    
    #new_reviews_file = extract_steam_reviews(apps_info, session)
    new_reviews_file = Path("new_reviews.jsonl.gz")
    #print("4/11")
    
    #new_yt_search_file = extract_youtube_info_1(apps_info)
    #print("5/11")
    
    new_yt_search_file = Path("new_info_steam_youtube.jsonl.gz")
    yt_search_data = read_file(new_yt_search_file)
    #new_yt_stats_file = extract_youtube_info_2(yt_search_data)
    new_yt_stats_file = Path("new_youtube_statistics.jsonl.gz")
    #print("6/11")

    #b_transformacion(new_gameinfo_file)
    print("7/11")
    
    #c_transformacion_youtube(new_yt_stats_file)
    print("8/11")
    
    #e_transformacion_imagenes(new_images_file)
    print("9/11")
    
    d_transformacion_reviews(new_reviews_file)
    print("10/11")

    crear_parquets_definitivos(
        pop_path=Path("new_games_info_popularity.parquet"),
        prices_path=Path("new_games_info_prices.parquet"),
        images_path=Path("new_P_info_imagenes.parquet"),
        youtube_path=Path("new_yt_stats.parquet")
    )
    print("11/11 - Done")

   