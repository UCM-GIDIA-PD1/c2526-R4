import requests
import Z_funciones

'''
Script que guarda la información procedente de appreviews

Requisitos:
Módulo requests para solicitar acceso a las APIs.

Entrada:
Necesita para su ejecución el archivo steam_apps.json

Salida:
Los datos se almacenan en la carpeta data/ en formato JSON.
'''

def get_resenyas(id, sesion):
    """
    Obtiene y procesa información relativa a las reseñas de un juego de Steam. Extrae
    las métricas más importantes que almacena en un diccionario.

    Args:
        id (int): Identificador númerico único de cada juego de Steam.
        sesion (requests.Session): Sesión persistente para las peticiones de HTTP.

    Returns:
        resenyas_juego (dict): Contiene un campo con la información general acerca de las 
        reseñas del juego (datos_resumen) y un campo que contiene la lista de reseñas (lista_resenyas). 
        En caso de que el request no se complete, se devuelve un diccionario vacío.
    """    
    # Obtiene las reseñas de un juego, como parámetros tiene filtro por idioma, aparecen ordenadas las reseñas por utilidad,
    # con un máximo de 100 reseñas por página. Por último se actualiza el cursor para obtener la url de la siguiente página
    url_begin = "https://store.steampowered.com/appreviews/"
    url = url_begin + str(id)
    resenyas_juego = {"datos_resumen": {}, "lista_resenyas": []}
    
    info = {"json":1, "language":"english", "purchase_type":"all", "filter":"all", "num_per_page":100,"cursor":"*"}
    data_json = Z_funciones.solicitud_url(sesion, info, url)
    if not data_json:
        return {}
    
    resenyas_juego["datos_resumen"] = data_json["query_summary"]
    
    # Contador para obtener sólo la primera página de resultados, en caso de querer obtener más páginas modificar el valor en
    # el while, si se quieren obtener todos las reseñas del juego, eliminar el parámetro cont
    cont = 0
    
    while (data_json["query_summary"].get("num_reviews") > 0 and cont < 1):
        # Por cada review obtiene los valores más importantes
        for review in data_json["reviews"]:
            resenya = {}
            resenya["id_resenya"] = review["recommendationid"]
            resenya["id_usuario"] = review["author"].get("steamid")
            resenya["texto"] = review["review"]
            resenya["valoracion"] = review["voted_up"]
            # El atributo peso determina la utilidad de la reseña, cuánto mayor es este mayor utilidad tiene la review,
            # el valor del peso puede ser string o int, esto debe ser tenido en cuenta a la hora de entrenar el modelo
            resenya["peso"] = review["weighted_vote_score"]
            resenya["early_access"] = review["written_during_early_access"]
            resenyas_juego["lista_resenyas"].append(resenya)
        
        # Actualiza el valor del cursor
        info["cursor"] = data_json["cursor"]
        
        # Se cargan los datos de la siguiente página de reviews
        data_json = Z_funciones.solicitud_url(sesion, info, url)
        if not data_json:
            return {}
        cont = cont + 1
    
    return resenyas_juego

def descargar_datos_juego(id, sesion):
    # Obtiene la info de un juego
    game_info = {"id": id, "resenyas": []}
    game_info["resenyas"] = get_resenyas(id, sesion)

    return game_info

def main():
    # El objeto de la sesión mejora el rendimiento cuando se hacen muchas requests a un mismo host
    sesion = requests.Session()
    lista_juegos = Z_funciones.cargar_datos_locales(r"data\steam_apps.json.gzip")
    if not lista_juegos:
        print("No se pudieron cargar los datos de los juegos")
        return
    print('Buscando reseñas de los juegos...\n')
    
    informacion_resenyas = {"data" : []}
    for juego in lista_juegos.get("apps"):
        data = descargar_datos_juego(juego["appid"], sesion)
        if data != {}:
            informacion_resenyas["data"].append(data)
            print(f"{juego["appid"]}: {juego["name"]}")
    
    # Escribe el contenido obtenido en un fichero json
    Z_funciones.guardar_datos_dict(informacion_resenyas, r"data\info_steam_resenyas.json.gzip")

if __name__ == "__main__":
    main()