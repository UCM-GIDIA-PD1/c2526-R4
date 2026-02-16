import os
import requests
from Z_funciones import solicitud_url, guardar_datos_dict, proyect_root
from tqdm import tqdm

"""
Script que itera sobre la API de Steam y devuelve un JSON comprimido con n juegos y sus APPID.

Requisitos:
- Módulo 'requests'.
- Tener API de steam.

Información extra:
- max_results tiene por defecto 10000 juegos, pero se puede ajustar hasta 50000.
- Usamos el parámetro last_appid para indicar el último juego que se extrajo.

Entrada:
- Ninguna.

Salida:
- Los datos se almacenan en la el directorio indicado.
"""


def A_lista_juegos():
    # url e info
    url = "https://api.steampowered.com/IStoreService/GetAppList/v1/"

    # Cogemos la API
    API_KEY = os.environ.get("STEAM_API_KEY")
    assert API_KEY, "La API_KEY no ha sido cargada"

    n_appids = 1000 # Cuantos appids quieres

    max_results = min(n_appids, 50000) # Cuantos resultados se quiere por request
    last_appid = 200000 # appid a partir del cual comienza a buscar, no se incluye en la respuesta
    info = {"key": API_KEY, "max_results" : max_results, "last_appid": last_appid}

    # Creamos el json que va a tener todos los datos
    content = []

    # Creamos la sesión
    session = requests.Session()
    
    # Bucle que itera sobre los elementos restantes de la lista de APPID de Steam
    print("Comenzando la extracción...")

    with tqdm(total=n_appids, desc="appids extraidos: ", unit="appids") as pbar:
        while n_appids > 0:
            # Si existe data lo guardamos en el diccionario content
            data = solicitud_url(session, info, url)
            
            if data:
                content.extend([str(app["appid"]) for app in data["response"].get("apps",[])])
            else:
                print("Carga fallida")
                return
            
            # Decrementamos el número de APPIDs restantes
            appids_extraidos = len(data["response"].get("apps",[]))
            pbar.update(appids_extraidos)
            n_appids -= appids_extraidos
            info["max_results"] = min(n_appids, 50000)

            # Si no hay más juegos salir del bucle y dar proceso por completado
            if not data["response"].get("have_more_results"):
                pbar.total = pbar.n
                pbar.refresh()
                break
            
            # Modificamos el last_appid con el último de la petición anterior
            info["last_appid"] = data["response"].get("last_appid")

    # Guardamos en un JSON
    json_dir = proyect_root() / "data" / "steam_apps.json.gz"

    guardar_datos_dict(content, json_dir)

    if os.path.exists(json_dir):
        print("Lista de juegos guardada correctamente")
    else:
        print("No se ha podido guardar la lista de juegos")

if __name__ == "__main__":
    A_lista_juegos()