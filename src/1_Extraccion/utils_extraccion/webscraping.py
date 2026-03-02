"""
Módulo enfocado al WebScraping que tiene como objectivo administrar la sesión de TOR (abrir y
rotar la IP), scrapeando directamente de YouTube.
"""

from DrissionPage import ChromiumPage, ChromiumOptions
from numpy import random as np_random
import stem.control
from psutil import process_iter
from subprocess import Popen, DEVNULL
from time import sleep
from random import choice
from src.utils.config import config_path
import platform

sys_platform = platform.system()

assert sys_platform == 'Windows' or sys_platform == 'Linux' or sys_platform == 'Darwin', "Sistema operativo no compatible"

if sys_platform == 'Windows':
    user_agents = [ 
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 OPR/115.0.0.0'
    ]
elif sys_platform == 'Linux':
    user_agents = [ 
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
        'Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 OPR/115.0.0.0'
    ]
elif sys_platform == 'Darwin': # Mac
    user_agents = [ 
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:140.0) Gecko/20100101 Firefox/140.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 OPR/115.0.0.0'
    ]

# Resoluciones de pantalla comunes:
common_resolutions = [
    (1920, 1080), (1366, 768), (1536, 864), 
    (1440, 900), (1280, 720), (1600, 900)
]

TORRC_DIR = config_path() / "torrc"

def _is_tor_running():
    """
    Verifica si el proceso del servicio Tor se encuentra actualmente en ejecución en el sistema.
    Itera sobre la lista de procesos activos y busca una coincidencia exacta con el nombre de tor.exe

    Args:
        Ninguno.

    Returns:
        bool: True si se encuentra un proceso llamado exactamente "tor.exe" activo, False en caso contrario.
    """
    tor_name = "tor.exe" if platform.system() == "Windows" else "tor"

    for process in process_iter(attrs=['pid', 'name']):
        try:
            if tor_name == process.info['name'].lower():
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
        print("Initializing TOR...")

        # Abrimos TOR (IMPORTANTE: hace falta tener la carpeta de TOR en PATH para que se pueda abrir)
        tor_name = "tor.exe" if platform.system() == "Windows" else "tor"
        Popen([tor_name, '-f', str(TORRC_DIR)], stdout=DEVNULL, stderr=DEVNULL)
        sleep(10)
        assert _is_tor_running(), "couldn't start TOR"
    else:
        print("TOR is running")

def renew_tor_ip(session):
    """
    Cierra la sesión pasada por parámetro, hace una rotación de IP y posteriormente
    crea otro ChromiumPage ya configurado con la nueva IP.

    Args:
        sesion (ChromiumPage): sesión de trabajo anterior.

    Returns:
        ChromiumPage: Nueva sesión de ChromiumPage con IP nueva.
    """
    print("Switching de IP")

    # Cerramos la sesión antigua
    if session:
        session.quit()

    # Rotación de IP
    try:
        with stem.control.Controller.from_port(port=9051) as controller:
            controller.authenticate()
            controller.signal(stem.Signal.NEWNYM)
            sleep(5)
    except stem.SocketError:
        print("Error: couldn't connect to Tor's control port (9051).")
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
    co.set_user_agent(np_random.choice(user_agents))
    co.set_argument('--proxy-server=socks5://127.0.0.1:9050') # Puerto que usa TOR
    co.set_argument('--password-store=basic') # Evitar que pida contraseña en Linux
    ancho_base, alto_base = choice(common_resolutions)
    alto = alto_base + np_random.randint(-20, 0) # Simulamos el tamaño de la barra de tareas de manera aleatoria
    co.set_argument(f'--window-size={ancho_base},{alto}')

    return ChromiumPage(co)

def search_youtube(game_name, date, session):
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
    nombre_formateado = game_name.replace(' ', '+')
    query = '%22' + nombre_formateado + '%22' + '+before%3A' + date
    url = "https://www.youtube.com/results?search_query=" + query + "&sp=CAM%253D"

    # Navegamos a la url
    session.get(url)

    try:
        # Scrapeamos hasta la sección de la columna de vídeos
        feed_videos = session.ele('tag:ytd-two-column-search-results-renderer')
        videos = feed_videos.eles("tag:ytd-video-renderer")
        lista_enlaces = []

        # Iteramos por los vídeos encontrados y devolvemos la lista de sus ids
        for v in videos:
            enlace = v.ele('#thumbnail').attr('href')
            # Nos aseguramos de lo que hemos buscado es un vídeo de formato largo
            if not 'shorts' in enlace and 'watch?v=' in enlace:
                id = enlace.split('&')[0].split('=')[1]
                lista_enlaces.append({"id":id})
        return lista_enlaces
    except:
        return []