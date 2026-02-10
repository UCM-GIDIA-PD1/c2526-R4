from DrissionPage import ChromiumPage, ChromiumOptions
import numpy as np
import stem.control
import psutil
import subprocess
import time

"""
Script que tiene como objetivo conseguir información YouTube interceptando los paquetes de red
usando una funcionalidad nativa que tiene DrissionPage, simplificando mucho la extracción de 
datos. Además, usa TOR para evitar baneos de IP por conexiones excesivas al buscar en YouTube.

Requisitos:
- Módulo `DrissionPage`.
- Tener TOR Bundle descargado.

Entrada:
- Archivo de info_steam_games.json

Salida:
- Los datos se almacenan en la el directorio indicado.
"""

# Cabezera aleatoria de navegación (SON DE WINDOWS, POR LO QUE NO SE DEBEN USAR ESTAS SI ESTÁS EN OTRO OS)
user_agents = [ 
'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0',
'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 OPR/115.0.0.0'
]

def is_tor_running():
    for process in psutil.process_iter(attrs=['pid', 'name']):
        try:
            if "tor.exe" in process.info['name'].lower():
                return True
        except:
            continue
    return False

def start_tor():
    if not is_tor_running():
        # Cambiar PATH de donde hayáis descargado TOR
        TOR_PATH = r"C:\PROGRAMS\TOR\tor\tor.exe"
        TORRC_PATH = r"C:\PROGRAMS\TOR\data\torrc"

        # Abrimos TOR
        subprocess.Popen(TOR_PATH, "-f", TORRC_PATH, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(20)

def renew_tor_ip(sesion):
    sesion.quit()
    with stem.control.Controller.from_port(port=9051) as controller:
        controller.authenticate()  
        controller.signal(stem.Signal.NEWNYM)
    
    # Configuramos la nueva sesion de DrissionPage
    co = ChromiumOptions()
    co.set_user_agent(np.random.choice(user_agents))
    co.set_argument('--proxy-server=socks5://127.0.0.1:9050')
    return ChromiumPage(co)

def main():
    # Definimos las opciones del navegador y cargamos la sesión
    start_tor()
    co = ChromiumOptions()
    co.set_user_agent(np.random.choice(user_agents))
    co.set_argument('--proxy-server=socks5://127.0.0.1:9050') # Puerto que usar TOR
    sesion = ChromiumPage(co)

    # url
    # Para comprobar que nos hemos metido en red tor correctamente: https://check.torproject.org
    cosa = "grand+theft+auto+v+before%3A2013-09-17"
    url = "https://www.youtube.com/results?search_query=" + cosa + "&sp=CAM%253D"

    # Navegamos
    #sesion.listen.start(targets='oembed', method="GET", res_type="fetch")
    sesion.get("https://check.torproject.org", interval=5)

    """
    sesion.wait(5, 0.5)
    res = sesion.listen.wait(count=1)
    if 'youtube.com' in res.url:
        print(f"Capturado con exito: {res.url}")
        print(res.response.body)
    
    sesion.quit()
    """

if __name__ == "__main__":
    main()