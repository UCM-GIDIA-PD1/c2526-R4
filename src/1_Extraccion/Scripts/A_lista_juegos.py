import os
import requests
import Z_funciones

"""
Script que itera sobre la API de Steam y devuelve un JSON comprimido con todos los juegos y sus APPID.

Requisitos:
- Módulo `requests`.
- Tener API de steam.

Información extra:
- max_results tiene por defecto 10000 juegos, pero se puede ajustar hasta 50000.
- Usamos el parámetro last_appid para indicar el último juego que se extrajo.

Entrada:
- Ninguna.

Salida:
- Los datos se almacenan en la el directorio indicado.
"""

def es_juego_valido(nombre):
    """
    Filtro preliminar para no gastar peticiones API en cosas que sabemos que no son juegos.

    Args:
        nombre (str): Nombre completo del juego
    
    Returns:
        bool : Devuelve False si detecta palabras clave de algo que no sea un juego, True en
            caso contrario
    """
    if not nombre: return False
    
    nombre_lower = nombre.lower()
    
    palabras_prohibidas = [
        "dedicated server", "server", "servidor",
        "soundtrack", " ost ", "original soundtrack",
        "bonus content", "artbook",
        "dlc", "expansion", "season pass",
        "demo", "playtest", "beta", "trial",
        "sdk", "editor", "tool", "driver", "wallpaper",
        "trailer", "teaser", "video"
    ]
    
    for palabra in palabras_prohibidas:
        if palabra in nombre_lower:
            return False
            
    return True

def main():
    # url e info
    url = "https://api.steampowered.com/IStoreService/GetAppList/v1/"

    # Cogemos la API
    API_KEY = os.environ.get('STEAM_API_KEY')
    if not API_KEY:
        print('La API_KEY no ha sido cargada')
        return

    max_results = 50000 # Poner a 50000 cuando se quiera extraer todo, 99 cuando se quiera extraer una prueba
    appid = 0 # Poner a 0 cuando se quiera extraer todo, otra APPID cuando se quiera empezar por un juego específico
    info = {"key": API_KEY, "max_results" : max_results, "last_appid": appid}

    # Creamos el json que va a tener todos los datos
    j = {"apps": []}

    # Hacemos el primer request a la API
    session = requests.Session()
    data = Z_funciones.solicitud_url(session, info, url)
    if data:
        j["apps"].extend([{"appid": a["appid"], "name": a["name"]} for a in data["response"].get("apps", []) 
                          if es_juego_valido(a.get("name"))])
    else:
        print("Carga fallida")
        return

    if max_results != 99:
        # Bucle que no para hasta que no hayan más resultados
        while data and data['response'].get('have_more_results'):
            info["last_appid"] = data['response'].get('last_appid')
            data = Z_funciones.solicitud_url(session, info, url)
            if data:
                j["apps"].extend([{"appid": a["appid"], "name": a["name"]} for a in data["response"].get("apps", []) 
                                  if es_juego_valido(a.get("name"))])
            else:
                print("Carga fallida")

    # Guardamos en un JSON
    Z_funciones.guardar_datos_dict(j, r"data\steam_apps.json.gzip")
    print("Lista de juegos guardada correctamente")

if __name__ == "__main__":
    main()