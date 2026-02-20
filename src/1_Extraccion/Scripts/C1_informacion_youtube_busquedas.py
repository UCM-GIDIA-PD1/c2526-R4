from utils.webscraping import start_tor, renew_tor_ip, new_configured_chromium_page, busqueda_youtube
from numpy import random
from time import time
from utils.sesion import tratar_existe_fichero, update_config, get_pending_games, overwrite_confirmation
from tqdm import tqdm
from utils.files import write_to_file, erase_file
from utils.config import youtube_scraping_file
import os

"""
Primera parte de la extracción de información de YouTube: búsqueda.

Script que tiene como objetivo conseguir información YouTube scrapeando directamente de 
Youtube. Además, usa TOR para evitar baneos de IP por conexiones excesivas al buscar, 
ya que es una petición costosa.

TOR es muy importante, a no ser que queráis baneos de IP de YouTube.

Requisitos:
- Tener TOR Bundle descargado.

Entrada:
- Archivo que contiene las características de los juegos

Salida:
- Los datos se almacenan en la el directorio indicado.
"""

def _intervalo_rotacion_IP():
    """Cambio de IP manual randomizado cada 5-6 minutos"""
    return 60 * random.uniform(5, 6)

def C1_informacion_youtube_busquedas(minio = False):
    try:
        start_idx, curr_idx, end_idx = -1,-1,-1
        pending_games, start_idx, curr_idx, end_idx = get_pending_games("C1")
        
        if not pending_games:
            print(f"No hay juegos en el rango [{curr_idx}, {end_idx}]")
            return

        # Si existe fichero preguntar si sobreescribir o insertar al final, esta segunda opción no controla duplicados
        if os.path.exists(youtube_scraping_file):
            mensaje = """El fichero de información de juegtos ya existe:\n\n1. Añadir contenido al fichero existente
2. Sobreescribir fichero\n\nIntroduce elección: """
            overwrite = tratar_existe_fichero(mensaje)
            if overwrite:
                # asegurarse de que se quiere eliminar toda la información
                if overwrite_confirmation():
                    erase_file(youtube_scraping_file)
                else:
                    print("Operación cancelada")
                    return
        # Lanzamos TOR
        start_tor()

        # Definimos las opciones del navegador y cargamos la sesión
        sesion = new_configured_chromium_page()

        # Iteramos sobre la lista de juegos
        ultima_marca_tiempo = time()
        intervalo = _intervalo_rotacion_IP()

        print('Comenzando extracción de juegos en YouTube...\n')
        with tqdm(pending_games, unit="juegos") as pbar:
            for juego in pbar:
                # Cargamos los datos
                appid = juego.get('id')
                nombre = juego.get('appdetails').get("name")
                fecha = juego.get('appdetails').get("release_date")
                pbar.set_description(f"Procesando appid {appid}")

                # Si se han cargado los datos correctamente, hacemos búsqueda en YouTube
                if nombre and fecha:
                    lista_ids = busqueda_youtube(nombre, fecha, sesion)
                    jsonl = {'id':appid,'name':nombre,'video_statistics':lista_ids}
                    write_to_file(jsonl, youtube_scraping_file, minio)
                    sesion.wait(4, scope=0.4) # Espera aleatoria de entre 2.4 y 5.6 segundos
                else:
                    tqdm.write(f'Juego con entrada incompleta: {nombre}')

                curr_idx += 1
                tiempo_actual = time()
                if tiempo_actual - ultima_marca_tiempo >= intervalo:
                    ultima_marca_tiempo = tiempo_actual
                    intervalo = _intervalo_rotacion_IP()
                    sesion = renew_tor_ip(sesion)
                    if not sesion:
                        break
    except KeyboardInterrupt:
        print("\n\nDetenido por el usuario. Guardando antes de salir...")
    finally:
        gamelist_info = {"start_idx" : start_idx, "curr_idx" : curr_idx, "end_idx" : end_idx}
        if curr_idx > end_idx:
            print("Rango completado")
        update_config("C1", gamelist_info)
        sesion.quit()

if __name__ == "__main__":
    # Poner a True para traer y mandar los datos a MinIO
    C1_informacion_youtube_busquedas(False)