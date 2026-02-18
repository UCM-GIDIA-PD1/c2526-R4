from DrissionPage import ChromiumPage, ChromiumOptions
import numpy as np
import stem.control
import psutil
import subprocess
import time
from Z_funciones import proyect_root
import random

"""
Módulo enfocado al WebScraping que tiene como objectivo administrar la sesión de TOR (abrir y
rotar la IP) y scrapear directamente de YouTube.
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

def _is_tor_running():
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
    if not _is_tor_running():
        print("Ejecutando TOR...")

        # Abrimos TOR (IMPORTANTE: hace falta tener la carpeta de TOR en PATH para que se pueda abrir)
        TORRC_DIR = proyect_root() / "config" / "torrc"
        subprocess.Popen(["tor.exe", '-f', TORRC_DIR], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        time.sleep(10)
        assert _is_tor_running(), "TOR no se ha ejecutado correctamente"
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