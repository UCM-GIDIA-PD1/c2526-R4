from DrissionPage import ChromiumPage, ChromiumOptions
import numpy as np
import stem.control
import psutil
import subprocess
import time
import Z_funciones
import random
import os

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

# Nota sobre user-agents (IMPORTANTE):
    # Estos son user-agent aleatorio para la navegación (SON DE WINDOWS, POR LO QUE NO SE DEBEN 
    # USAR ESTAS SI ESTÁS EN OTRO OS). Esto lo hacemos para evitar que nuestro agent sea detectado
    # como el mismo por la huella digital que deja nuestro navegador por la web (ya que nos podrían
    # identificar por nuestro Software y Hardware aunque configuremos TOR):
user_agents = [ 
'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0',
'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 OPR/115.0.0.0'
]

# Resoluciones de pantalla comunes:
resoluciones_comunes = [
    (1920, 1080), (1366, 768), (1536, 864), 
    (1440, 900), (1280, 720), (1600, 900)
]

def is_tor_running():
    """
    Verifica si el proceso del servicio Tor se encuentra actualmente en ejecución en el sistema.
    Itera sobre la lista de procesos activos y busca una coincidencia exacta con el nombre de tor.exe

    Args:
        Ninguno.

    Returns:
        bool: True si se encuentra un proceso llamado exactamente "tor.exe" activo, False en caso contrario.
    """
    for process in psutil.process_iter(attrs=['pid', 'name']):
        try:
            if "tor.exe" == process.info['name'].lower():
                return True
        except:
            continue
    return False

def start_tor():
    """
    Inicia el servicio de Tor si no se detecta su ejecución previa en el sistema operativo.

    Args:
        Ninguno.

    Returns:
        None: La función realiza una acción de sistema y no devuelve ningún valor.
    """
    if not is_tor_running():
        print("Ejecutando TOR...")
        # Cambiar PATH de donde hayáis descargado TOR
        TOR_PATH = r"C:\PROGRAMS\TOR\tor\tor.exe"
        TORRC_PATH = r"C:\PROGRAMS\TOR\data\torrc"

        # Abrimos TOR
        subprocess.Popen([TOR_PATH, '-f', TORRC_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(10)
    else:
        print("TOR ya está siendo ejecutado")

def renew_tor_ip(sesion):
    """
    Cierra la sesión pasada por parámetro, hace una rotación de IP y posteriormente
    crea otro ChromiumPage ya configurado con la nueva IP.

    Args:
        sesion (ChromiumPage): sesión de trabajo anterior. 

    Returns:
        ChromiumPage: Nueva sesión de ChromiumPage con IP nueva.
    """
    print("Cambiamos de IP")

    # Cerramos la sesión antigua
    sesion.quit()

    # Rotación de IP
    try:
        with stem.control.Controller.from_port(port=9051) as controller:
            controller.authenticate()
            controller.signal(stem.Signal.NEWNYM)
    except stem.SocketError:
        print("Error: No se pudo conectar con el puerto de control de Tor (9051).")
        return None
    
    # Configuramos la nueva sesion de DrissionPage
    return new_configured_chromium_page()

def new_configured_chromium_page():
    """
    Abre una nueva sesión configurada de ChromiumPage y la devuelve para intentar
    tener anonimizar la huella del navegador.

    Args:
        Ninguno.

    Returns:
        ChromiumPage: Nueva sesión de ChromiumPage ya configurada.
    """
    co = ChromiumOptions()
    
    # Configuramos el nuevo ChromiumPage
    co.set_user_agent(np.random.choice(user_agents))
    co.set_argument('--proxy-server=socks5://127.0.0.1:9050') # Puerto que usa TOR
    ancho_base, alto_base = random.choice(resoluciones_comunes)
    alto = alto_base + np.random.randint(-20, 0) # Simulamos el tamaño de la barra de tareas de manera aleatoria
    co.set_argument(f'--window-size={ancho_base},{alto}')

    return ChromiumPage(co)

def busqueda_youtube(nombre_juego, fecha, sesion):
    """
    Scrapea YouTube a partir del nombre del juego, la fecha de salida para buscar
    antes de la misma, y la sesión de DrissionPage actual.

    Args:
        nombre_juego (str): nombre completo del juego. 
        fecha (str): fecha en formato YYYY-MM-DD.
        sesion (ChromiumPage): sesión de trabajo actual. 

    Returns:
        list: Devuelve una lista de diccionarios con IDs de vídeos de YouTube de
            la búsqueda de los juegos
    """
    # url
    nombre_formateado = nombre_juego.replace(' ', '+')
    query = '%22' + nombre_formateado + '%22' + '+before%3A' + fecha
    url = "https://www.youtube.com/results?search_query=" + query + "&sp=CAM%253D"

    # Navegamos
    sesion.get(url)
    feed_videos = sesion.ele('tag:ytd-two-column-search-results-renderer')
    videos = feed_videos.eles("tag:ytd-video-renderer")
    lista_enlaces = []
    for v in videos:
        enlace = v.ele('#thumbnail').attr('href')
        if not 'shorts' in enlace and 'watch?v=' in enlace:
            id = enlace.split('&')[0].split('=')[1]
            lista_enlaces.append({"id":id})
    
    return lista_enlaces

def C1_informacion_youtube_busquedas():
    # Iniciamos TOR: es recomendable hacer sesion.get() aquí para comprobar red TOR: https://check.torproject.org
    start_tor()

    # Cargamos los puntos de inicio y final
    ruta_config = r"data\config_rango.txt" # Necesario crear el archivo y poner los datos como se indica en Z_funciones.leer_configuracion()
    juego_ini, juego_fin = Z_funciones.leer_configuracion(ruta_config)

    # Rutas que van a ser usadas
    ruta_origen = r'data\info_steam_games.json.gz'
    ruta_temp_jsonl = f"data\\temp_session_{juego_ini}_{juego_fin}.jsonl"
    ruta_final_gzip = r"data\info_steam_youtube_1.json.gz"

    if os.path.exists(ruta_temp_jsonl):
        os.remove(ruta_temp_jsonl)

    # Cargamos el JSON comprimido de la información de los juegos
    juegos = Z_funciones.cargar_datos_locales(ruta_origen)
    if not juegos:
        print('Error al cargar los juegos')
        return

    j = juegos.get("data", [])
    if juego_fin >= len(j):
        juego_fin = len(j) - 1
    
    juegos_a_procesar = j[juego_ini : juego_fin + 1]

    print(f"Sesión configurada: del índice {juego_ini} al {juego_fin}")
    print('Comenzando extracción de juegos en YouTube...\n')

    # Definimos las opciones del navegador y cargamos la sesión
    sesion = new_configured_chromium_page()

    # Iteramos sobre la lista de juegos
    ultima_marca_tiempo = time.time()
    intervalo = 60 * np.random.uniform(5, 6) # Cambio de IP manual cada 5-6 minutos

    idx_actual = juego_ini - 1
    ultimo_idx_guardado = juego_ini - 1
    try:
        for i, juego in enumerate(Z_funciones.barra_progreso(juegos_a_procesar, keys=['id'])):
            id = juego.get('id')
            nombre = juego.get('appdetails').get("name")
            fecha = juego.get('appdetails').get("release_date").get("date")
            fecha_formateada = Z_funciones.convertir_fecha_steam(fecha)
            idx_actual = i + juego_ini
        
            if nombre and fecha_formateada:
                lista_ids = busqueda_youtube(nombre, fecha_formateada, sesion)
                Z_funciones.guardar_datos_dict({'id':id,'name':nombre,'video_statistics':lista_ids}, ruta_temp_jsonl)
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
        print("\nDetenido por el usuario. Guardando antes de salir...")
    finally:
        Z_funciones.cerramos_sesion(ruta_temp_jsonl, ruta_final_gzip, ruta_config, ultimo_idx_guardado, juego_fin)        
        sesion.quit()

if __name__ == "__main__":
    C1_informacion_youtube_busquedas()