from utils.webscraping import start_tor, renew_tor_ip, new_configured_chromium_page, busqueda_youtube
import numpy as np
import time
import utils.sesion

"""
Primera parte de la extracción de información de YouTube: búsqueda.

Script que tiene como objetivo conseguir información YouTube scrapeando directamente de 
Youtube. Además, usa TOR para evitar baneos de IP por conexiones excesivas al buscar, 
ya que es una petición costosa.

TOR es muy importante, a no ser que queráis baneos de IP de YouTube.

Requisitos:
- Módulo `DrissionPage`.
- Módulo `stem`.
- Tener TOR Bundle descargado.

Entrada:
- Archivo de info_steam_games.json.gz.

Salida:
- Los datos se almacenan en la el directorio indicado.
"""

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
    ultima_marca_tiempo = time.time()
    intervalo = 60 * np.random.uniform(5, 6) # Cambio de IP manual cada 5-6 minutos

    print('Comenzando extracción de juegos en YouTube...\n')
    idx_actual = juego_ini - 1
    ultimo_idx_guardado = juego_ini - 1
    try:
        for i, juego in enumerate(XXXXX.barra_progreso([x[1] for x in juegos_pendientes], keys=['id'])):
            id = juego.get('id')
            nombre = juego.get('appdetails').get("name")
            fecha = juego.get('appdetails').get("release_date").get("date")
            fecha_formateada = XXXXX.convertir_fecha_steam(fecha)
            idx_actual = i + juego_ini
        
            if nombre and fecha_formateada:
                lista_ids = busqueda_youtube(nombre, fecha_formateada, sesion)
                XXXXX.guardar_datos_dict({'id':id,'name':nombre,'video_statistics':lista_ids}, ruta_temp_jsonl)
                ultimo_idx_guardado = idx_actual
            else:
                print(f'Juego con entrada incompleta: {nombre}')
        
            sesion.wait(4, scope=0.4)
            tiempo_actual = time.time()
            if tiempo_actual - ultima_marca_tiempo >= intervalo:
                ultima_marca_tiempo = tiempo_actual
                intervalo = 60 * np.random.uniform(5, 6) # Cambio de IP manual cada 5-6 minutos
                sesion = renew_tor_ip(sesion)
                if not sesion:
                    break
    except KeyboardInterrupt:
        print("\n\nDetenido por el usuario. Guardando antes de salir...")
    finally:
        utils.sesion.cerrar_sesion(ruta_temp_jsonl, ruta_final_gzip, ruta_config, ultimo_idx_guardado, juego_fin, minio)        
        sesion.quit()

if __name__ == "__main__":
    # Poner a True para traer y mandar los datos a MinIO
    C1_informacion_youtube_busquedas(False)