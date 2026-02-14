import os
import requests
import Z_funciones
from pathlib import Path

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

    n_appids = 200000 # Cuantos appids quieres

    max_results = min(n_appids, 50000) # Cuantos resultados se quiere por request
    last_appid = 0 # appid a partir del cual comienza a buscar, no se incluye en la respuesta
    info = {"key": API_KEY, "max_results" : max_results, "last_appid": last_appid}

    # Creamos el json que va a tener todos los datos
    content = {"data": []}

    # Creamos la sesión
    session = requests.Session()
    
    # Bucle que itera sobre los elementos restantes de la lista de APPID de Steam
    print("Comenzando la extracción...")
    while n_appids > 0:
        # Si existe data lo guardamos en el diccionario content
        data = Z_funciones.solicitud_url(session, info, url)
        if data:
            content["data"].extend([{"id": app["appid"]} for app in data["response"].get("apps",[])])
        else:
            print("Carga fallida")
            return
        
        # Decrementamos el número de APPIDs restantes
        n_appids -= len(data["response"].get("apps",[]))
        info["max_results"] = min(n_appids, 50000)

        # Si no hay respuesta, break
        if not data["response"].get("have_more_results"):
            break
        
        # Modificamos el last_appid con el último de la petición anterior
        info["last_appid"] = data["response"].get("last_appid")

    print(f"Se han extraido {len(content.get("data"))} juegos")

    # Guardamos en un JSON
    json_dir = Path(__file__).resolve().parents[3] / "data" / "steam_apps.json.gz"
    Z_funciones.guardar_datos_dict(content, json_dir)

    if os.path.exists(json_dir):
        print("Lista de juegos guardada correctamente")
    else:
        print("No se ha podido guardar la lista de juegos")

if __name__ == "__main__":
    A_lista_juegos()