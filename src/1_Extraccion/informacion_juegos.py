import json
import requests
from bs4 import BeautifulSoup

'''
Este script guarda tanto la información de appdetails (categorías, links de imágenes,
precios...) y el número de reviews del primer mes.

Necesita una lista de juegos con appid
'''

def cargar_datos_locales(ruta_archivo):
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            datos = json.load(archivo)
        return datos
    except FileNotFoundError:
        print(f"Error: El archivo en {ruta_archivo} no existe.")
        return None
    except json.JSONDecodeError:
        print("Error: El archivo no tiene un formato JSON válido.")
        return None

def get_appdetails(id):
    # Creamos la url
    url_begin = "https://store.steampowered.com/api/appdetails?appids="
    url_end = "&cc=eur"
    url = url_begin + str(id) + url_end

    # Hacemos el request a la página y creamos el json que va a almacenar la info
    appdetails = {}
    data = requests.get(url).json()

    # Metemos la información útil
    appdetails["name"] = data[str(id)]["data"].get("name")
    appdetails["required_age"] = data[str(id)]["data"].get("required_age")
    if not data[str(id)]["data"].get("price_overview"):
        # Si el juego no tiene price_overview significa que es gratis, por lo que 
        # metemos nosotros los valores a 0
        appdetails["price_overview"] = {}
        appdetails["price_overview"]["currency"] = "EUR"
        appdetails["price_overview"]["initial"] = 0
        appdetails["price_overview"]["final"] = 0
        appdetails["price_overview"]["discount_percent"] = 0
        appdetails["price_overview"]["initial_formatted"] = ""
        appdetails["price_overview"]["final_formatted"] = "0€"
    else:
        # Si el juego no es gratis copiamos el price_overview directamente de data
        appdetails["price_overview"] = data[str(id)]["data"].get("price_overview")

    # Limpiamos los lenguajes a los que están traducidos el juego
    languages_raw_bs4 = BeautifulSoup(data[str(id)]["data"].get("supported_languages"), features="lxml").text
    clean_text = str(languages_raw_bs4).replace("idiomas con localización de audio", "").replace("*", "")
    supported_languages = [lang.strip() for lang in clean_text.split(",")]
    appdetails["supported_languages"] = list(set(supported_languages))

    # Copiamos más información
    appdetails["capsule_img"] = data[str(id)]["data"].get("capsule_imagev5")
    appdetails["header_img"] = data[str(id)]["data"].get("header_image")
    appdetails["screenshots"] = data[str(id)]["data"].get("screenshots")

    appdetails["developers"] = data[str(id)]["data"].get("developers")
    appdetails["publishers"] = data[str(id)]["data"].get("publishers")

    appdetails["categories"] = data[str(id)]["data"].get("categories")
    appdetails["genres"] = data[str(id)]["data"].get("genres")

    appdetails["release_date"] = data[str(id)]["data"].get("release_date")

    return appdetails

def get_appreviewhistogram(id):
    # Creamos la url
    url_begin = "https://store.steampowered.com/appreviewhistogram/"
    url_end = "?l=english"
    url = url_begin + str(id) + url_end

    # Hacemos el request a la página y creamos el json que va a almacenar la info
    appreviewhistogram = {}
    data = requests.get(url).json()

    # Caso en el que no haya ninguna review: los rellups están vacíos
    if not data["results"].get("rollups"):
        return {}

    appreviewhistogram["start_date"] = data["results"]["start_date"]
    appreviewhistogram["end_date"] = data["results"]["end_date"]
    appreviewhistogram["rollup_type"] = data["results"]["rollup_type"]

    # Cogemos los datos de aproximadamente el primer mes (las valoraciones del primer mes)
    if appreviewhistogram["rollup_type"] == "week":
        l = {"date": data["results"]["rollups"][0].get("date"), "recommendations_up": 0, "recommendations_down": 0}
        for i in range(0, 4):
            l["recommendations_up"] += data["results"]["rollups"][i].get("recommendations_up")
            l["recommendations_down"] += data["results"]["rollups"][i].get("recommendations_down")
        appreviewhistogram["rollups"] = l
    else:
        appreviewhistogram["rollups"] = {"date": data["results"]["rollups"][0].get("date"), 
             "recommendations_up": data["results"]["rollups"][0].get("recommendations_up"), 
             "recommendations_down": data["results"]["rollups"][0].get("recommendations_down")}

    return appreviewhistogram

def descargar_datos_juego(id):
    game_info = {"id": id, "appdetails": {}, "appreviewhistogram": {}}
    game_info["appdetails"] = get_appdetails(id)
    game_info["appreviewhistogram"] = get_appreviewhistogram(id)
    if game_info["appreviewhistogram"] == {}:
        # Si el appreviewhistogram está vacío, significa que el juego no tiene reseñas
        return {}
    else:
        return game_info

def main():
    # Cargamos el json de la lista de juegos (archivo de lista_juegos.py)
    lista_juegos = cargar_datos_locales(r"data\steam_apps.json")
    
    # Iteramos sobre la lista de juegos y lo metemos en un json nuevo
    informacion_juegos = {"data":[]}
    for juego in lista_juegos["response"].get("apps"):
        desc = descargar_datos_juego(juego.get("appid"))
        if desc != {}:
            informacion_juegos["data"].append(desc)
    
    # Metemos la información en un json
    with open(r"data\info_steam_games.json", "w", encoding = "utf-8") as f:
        json.dump(informacion_juegos, f, ensure_ascii = False, indent = 2)

if __name__ == "__main__":
    main()