import os
import requests
import Z_funciones

"""
Script que itera sobre la API de Steam y devuelve un JSON con todos los juegos y sus APPID.

Requisitos:
- Módulo `requests`.
- Tener API de steam.

Información extra:
- max_results tiene por defecto 10000 juegos, pero se puede ajustar hasta 50000.
- Usamos el parámetro last_appid para indicar el último juego que se extrajo

Salida:
- Los datos se almacenan en la el directorio indicado.
"""

def main():
    # url e info
    url = "https://api.steampowered.com/IStoreService/GetAppList/v1/"

    # Cogemos la API
    API_KEY = os.environ.get('STEAM_API_KEY')
    if not API_KEY:
        print('La API_KEY no ha sido cargada')
        return

    # Vamos a poner max_results = 99 para tener una muestra pequeña de prueba
    max_results = 99 # Poner a 50000 cuando se quiera extraer todo
    info = {"key": API_KEY, "max_results" : max_results, "last_appid": 0}

    # Creamos el json que va a tener todos los datos
    j = {"apps": []}

    # Hacemos el primer request a la API
    session = requests.Session()
    data = Z_funciones.solicitud_url(session, info, url)
    if data:
        j["apps"].extend([{"appid": a["appid"], "name": a["name"]} for a in data["response"].get("apps", [])])
    else:
        print("Carga fallida")
        return

    if max_results != 99:
        # Bucle que no para hasta que no hayan más resultados
        while data and data['response'].get('have_more_results'):
            info["last_appid"] = data['response'].get('last_appid')
            data = Z_funciones.solicitud_url(session, info, url)
            if data:
                j["apps"].extend([{"appid": a["appid"], "name": a["name"]} for a in data["response"].get("apps", [])])
            else:
                print("Carga fallida")

    # Guardamos en un JSON
    Z_funciones.guardar_datos_json(j, r"data\steam_apps.json")
    print("Lista de juegos guardada correctamente")

if __name__ == "__main__":
    main()