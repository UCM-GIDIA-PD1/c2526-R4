from utils.webscraping import start_tor, renew_tor_ip, new_configured_chromium_page, busqueda_youtube
from numpy import random
from time import time
import utils.sesion
from tqdm import tqdm
from utils.date import format_date_string
from utils.files import write_to_file

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
    intervalo = 60 * random.uniform(5, 6)
    return intervalo

def C1_informacion_youtube_busquedas(minio = False): # PARA TERMINAR SESIÓN: CTRL + C
    # Lanzamos TOR
    start_tor()

    # Cargamos los datos
    origin = "info_steam_games.json.gz"
    final = "info_steam_youtube1.json.gz"
    juego_ini, juego_fin, juegos_pendientes, ruta_temp_jsonl, ruta_final_gzip, ruta_config = utils.sesion.abrir_sesion(origin, final, False, minio)
    if not juego_ini:
        return

    # Definimos las opciones del navegador y cargamos la sesión
    sesion = new_configured_chromium_page()

    # Iteramos sobre la lista de juegos
    ultima_marca_tiempo = time()
    intervalo = _intervalo_rotacion_IP()

    print('Comenzando extracción de juegos en YouTube...\n')
    idx_actual = juego_ini
    try:
        with tqdm(juegos_pendientes, unit="juegos") as pbar:
            for i, juego in enumerate(pbar):
                # Cargamos los datos
                appid = juego.get('appid')
                nombre = juego.get('appdetails').get("name")
                fecha = juego.get('appdetails').get("release_date").get("date")
                fecha_formateada = format_date_string(fecha)
                pbar.set_description(f"Procesando appid: {appid}")

                # Si se han cargado los datos correctamente, hacemos búsqueda en YouTube
                if nombre and fecha_formateada:
                    lista_ids = busqueda_youtube(nombre, fecha_formateada, sesion)
                    write_to_file({'id':id,'name':nombre,'video_statistics':lista_ids}, ruta_temp_jsonl)
                else:
                    tqdm.write(f'Juego con entrada incompleta: {nombre}')

                idx_actual += i
                sesion.wait(4, scope=0.4)
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
        utils.sesion.cerrar_sesion(ruta_temp_jsonl, ruta_final_gzip, ruta_config, idx_actual, juego_fin, minio)        
        sesion.quit()

if __name__ == "__main__":
    # Poner a True para traer y mandar los datos a MinIO
    C1_informacion_youtube_busquedas(False)