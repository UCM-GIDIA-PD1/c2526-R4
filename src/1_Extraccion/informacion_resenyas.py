import json
import requests

'''
Este script guarda las reseñas de la primera página (en general 100 reseñas) de steam
de un juego a partir de us appid

Necesita una lista de juegos con appid
'''

def cargar_datos_locales(ruta_archivo):
    # Carga del archivo json
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

def get_resenyas(id):
    # Obtiene las reseñas de un juego, como parámetros tiene filtro por idioma, y aparecen ordenadas las reseñas por utilidad,
    # con un máximo de 100 reseñas por página. Por último se actualiza el cursor para obtener la url de la siguiente página
    url_begin = "https://store.steampowered.com/appreviews/"
    
    url = url_begin + str(id)
    resenyas_juego = {"datos_resumen": {}, "lista_resenyas": []}
    
    info = {"json":1, "languaje":"english", "purchase_type":"all", "filter":"all", "num_per_page":100,"cursor":"*"}
    data = requests.get(url, params = info).json()
    
    resenyas_juego["datos_resumen"] = data["query_summary"]
    
    # Contador para obtener sólo la primera página de resultados, en caso de querer obtener más páginas modificar el valor en
    # el while, si se quieren obtener todos los juegos, eliminar el parámetro cont
    cont = 0
    
    while (data["query_summary"].get("num_reviews") > 0 and cont < 1):
        # Por cada review obtiene los valores más importantes
        for review in data["reviews"]:
            resenya = {}
            resenya["id_resenya"] = review["recommendationid"]
            resenya["id_usuario"] = review["author"].get("steamid")
            resenya["texto"] = review["review"]
            resenya["valoracion"] = review["voted_up"]
            # El atributo peso determina la utilidad del comentario, cuánto mayor es este mayor utilidad tiene la review,
            # el valor del peso puede ser string o int, esto debe ser tenido en cuenta a la hora de entrenar el modelo
            resenya["peso"] = review["weighted_vote_score"]
            
            resenya["early_access"] = review["written_during_early_access"]
            
            resenyas_juego["lista_resenyas"].append(resenya)
        
        # Actualiza el valor del cursor
        info["cursor"] = data["cursor"]
        
        # se cargan los datos de la siguiente página
        data = requests.get(url, params = info).json()
        cont = cont + 1
        
    return resenyas_juego

def descargar_datos_juego(id):
    # Obtiene las info de un juego
    game_info = {"id": id, "resenyas": []}
    game_info["resenyas"] = get_resenyas(id)

    return game_info

def main():
    lista_juegos = cargar_datos_locales(r"extraccion_datos\juegos_steam_99.json")
    informacion_resenyas = {"data" : []}
    for juego in lista_juegos["response"].get("apps"):
        informacion_resenyas["data"].append(descargar_datos_juego(juego["appid"]))
    
    with open("info_steam_games.json", "w", encoding = "utf-8") as f:
        json.dump(informacion_resenyas, f, ensure_ascii = False, indent = 2)

if __name__ == "__main__":
    main()