from DrissionPage import ChromiumPage, ChromiumOptions
import numpy as np
import stem.control
import psutil
import subprocess
import time
import Z_funciones
import time

"""
Script que tiene como objetivo conseguir información YouTube scrapeando directamente de 
Youtube. Además, usa TOR para evitar baneos de IP por conexiones excesivas al buscar, 
ya que es una petición costosa.

Requisitos:
- Módulo `DrissionPage`.
- Tener TOR Bundle descargado.

Entrada:
- Archivo de info_steam_games.json

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

        # Abrimos TOR
        subprocess.Popen(TOR_PATH, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
    with stem.control.Controller.from_port(port=9051) as controller:
        controller.authenticate()
        controller.signal(stem.Signal.NEWNYM)
    
    # Configuramos la nueva sesion de DrissionPage
    co = ChromiumOptions()
    co.set_user_agent(np.random.choice(user_agents))
    co.set_argument('--proxy-server=socks5://127.0.0.1:9050')
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

def main():
    # Iniciamos TOR: es recomendable hacer sesion.get() aquí para comprobar red TOR: https://check.torproject.org
    start_tor()

    # Cargamos los datos del JSON que contiene las fechas para hacer las búsqueda correctamente
    ruta_json = r'data\info_steam_games.json.gzip'
    juegos = Z_funciones.cargar_datos_locales(ruta_json)

    if not juegos:
        print('Error al cargar los juegos')
        return
    print('Buscando juegos en YouTube...\n')
    lista_juegos = juegos.get("data")

    # Definimos las opciones del navegador y cargamos la sesión
    co = ChromiumOptions()
    co.set_user_agent(np.random.choice(user_agents))
    co.set_argument('--proxy-server=socks5://127.0.0.1:9050') # Puerto que usa TOR
    sesion = ChromiumPage(co)

    # Iteramos sobre la lista de juegos
    ultima_marca_tiempo = time.time()
    intervalo = 60 * np.random.uniform(1, 2)
    for juego in lista_juegos:
        nombre = juego.get('appdetails').get("name")
        fecha = juego.get('appdetails').get("release_date").get("date")
        fecha_formateada = Z_funciones.convertir_fecha_steam(fecha)
        
        if nombre and fecha_formateada:
            print(f"{nombre}: {fecha}")
            lista_ids = busqueda_youtube(nombre, fecha_formateada, sesion)
            juego["video_statistics"] = lista_ids
        else:
            print(f'Juego con entrada incompleta: {nombre}')
        
        sesion.wait(4, scope=0.4)
        tiempo_actual = time.time()
        if tiempo_actual - ultima_marca_tiempo >= intervalo:
            ultima_marca_tiempo = tiempo_actual
            intervalo = 60 * np.random.uniform(5, 6)

    # Guardamos datos y cerramos la sesión
    Z_funciones.guardar_datos_dict(lista_juegos, r"data\info_steam_games_and_semiyoutube.json.gzip")
    sesion.quit()

if __name__ == "__main__":
    main()