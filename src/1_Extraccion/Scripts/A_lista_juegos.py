import os
import requests
import Z_funciones

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

    n_appids = 200000  # Cuantos appids quieres

    max_results = min(n_appids, 50000) # Cuantos resulatados se quiere por request
    last_appid = 0 # appid a partir del cual comienza a buscar, no se incluye en la respuesta
    info = {"key": API_KEY, "max_results" : max_results, "last_appid": last_appid}

    # Creamos el json que va a tener todos los datos
    content = {"apps": []}

    session = requests.Session()
    
    # hay más elementos que cargar
    while n_appids > 0:
        data = Z_funciones.solicitud_url(session, info, url)

        if data:
            content["apps"].extend([{"appid": app["appid"]} for app in data["response"].get("apps",[]) if es_juego_valido(app.get("name"))])
        else:
            print("Carga fallida")
            return
        
        n_appids -= len(data["response"].get("apps",[]))
        
        info["max_results"] = min(n_appids, 50000)

        if not data["response"].get("have_more_results"):
            print("No hay más resultados")
            break

        info["last_appid"] = data["response"].get("last_appid")
        

    # Guardamos en un JSON
    Z_funciones.guardar_datos_dict(content, r"data\steam_apps.json.gz")
    print("Lista de juegos guardada correctamente")

if __name__ == "__main__":
    A_lista_juegos()