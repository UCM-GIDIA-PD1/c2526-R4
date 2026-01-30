import os
import requests
import json

"""
Script que itera sobre la API de Steam y devuelve un JSON con todos los juegos y sus APPID.

Requisitos:
- Módulo `requests`.

Información extra:
- max_results tiene por defecto 10000 juegos, pero se puede ajustar hasta 50000.
- Usamos el parámetro last_appid para indicar el último juego que se extrajo

Salida:
- Los datos se almacenan en la el directorio indicado.
"""

# url e info
url = "https://api.steampowered.com/IStoreService/GetAppList/v1/"
info = {"key": os.environ.get("STEAM_API_KEY"), "max_results" : 50000, "last_appid": 0}

# creamos el json que va a tener todos los datos
j = {"apps": []}

# hacemos el primer request a la API
data = requests.get(url, params= info).json()
j["apps"].extend([{"appid": a["appid"], "name": a["name"]} for a in data["response"].get("apps", [])])

# bucle que no para hasta que no hayan más resultados
while data['response'].get('have_more_results'):
    info["last_appid"] = data['response'].get('last_appid')
    data = requests.get(url, params= info).json()
    # insertamos los datos en nuestro json
    j["apps"].extend([{"appid": a["appid"], "name": a["name"]} for a in data["response"].get("apps", [])])

# Escribir en un fichero json
with open("steam_apps.json", "w", encoding = "utf-8") as f:
    json.dump(j, f, ensure_ascii = False, indent = 2)