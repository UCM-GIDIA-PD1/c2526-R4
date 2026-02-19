import os
from utils.config import appidlist_file, appidlist_info_file
from utils.files import read_file, write_to_file
from utils.steam_requests import get_appids

# NOTA: HACE FALTA AÑADIR VINCULACIÓN CON MINIO y AÑADIR ARCHIVO DE CONFIGURACIÓN JSON PARA GUARDAR INFO DE SCRIPT A

"""
Script que itera sobre la API de Steam y devuelve un JSON comprimido con n juegos y sus APPID.

Requisitos:
- Tener API de steam.

Información extra:
- max_results tiene por defecto 10000 juegos, pero se puede ajustar hasta 50000.
- Usamos el parámetro last_appid para indicar el último juego que se extrajo.

Entrada:
- Ninguna.

Salida:
- Se almacena una lista de los APPIDs.
"""

def _handle_input(initial_message, isResponseValid = lambda x: True):
    """
    Función que maneja la entrada. Por defecto la función siempre devuelve True.

    Args:
        mensaje (str): mensaje inicial. 
        isResponseValid (function): función que verifica la validez de un input dado.

    Returns:
        boolean: True si el input es correcto, false en caso contrario.
    """
    respuesta = input(initial_message).strip()

    # Hasta que no se dé una respuesta válida no se puede salir del bucle
    while not isResponseValid(respuesta):
        respuesta = input("Opción no válida, prueba de nuevo: ").strip()
    
    return respuesta

def _tratar_existe_fichero():
    """
    Menú con opción de añadir contenido al fichero existente o sobreescribirlo.
    
    returns:
        boolean: True si sobreescribir archivo meter appids nuevos, False en caso contrario
    """

    mensaje = """El fichero de lista de appids ya existe:\n\n1. Añadir contenido al fichero existente
2. Sobreescribir fichero\n\nIntroduce elección: """

    def _isValid(respuesta):
        valid_inputs ={"1", "2"}
        return respuesta in valid_inputs

    respuesta = _handle_input(mensaje, _isValid)
    return True if respuesta == "2" else False
    
def _parametros_de_request():
    mensaje = """Elige modo de ejecución:\n\n1. Elegir manualmente el los parámetros\n2. Extraer nuevos juegos\n
Introduce elección: """
    # El input es "1" o "2"
    def _isValid(respuesta):
        valid_inputs ={"1", "2"}
        return respuesta in valid_inputs
    
    respuesta = _handle_input(mensaje, _isValid)
    n_appids = 0
    last_appid = 0

    # El input es un número entero
    def _isValid(respuesta):
        return respuesta.isdigit()
    
    if respuesta == "1": # Elegir manualmente el los parámetros
        mensaje = "Número de appids a extraer: "
        n_appids = int(_handle_input(mensaje, _isValid))
        
        mensaje = "Appid desde el que hay que extraer: "
        last_appid = int(_handle_input(mensaje, _isValid))

    elif respuesta == "2": # Extraer nuevos juegos
        mensaje = "Número de appids nuevos a extraer: "
        n_appids = int(_handle_input(mensaje, _isValid))
        info = read_file(appidlist_info_file)
        if info is None:
            appid_list = read_file(appidlist_file)
            last_appid = appid_list[-1]
        else:
            last_appid = info["last_appid"]

    return int(n_appids), str(last_appid)


def A_lista_juegos():
    """
    Obtiene la lista completa de appids de los juegos de Steam

    Args:
        minio (bool): Activar para descargar los datos al servidor de MinIO en vez de en local
    
    Returns:
        None
    """
    data = []
    seen = set()

    # Si existe lista anterior, ¿se quiere sobreescribir o seguir a partir del mismo?
    if os.path.exists(appidlist_file):
        overwrite_file = _tratar_existe_fichero()
        if not overwrite_file:
            old_data = read_file(appidlist_file)
            data.extend(old_data)
            seen = set(data)

    # Parámetros de request
    n_appids, last_appid = _parametros_de_request()
    new_data = get_appids(n_appids, last_appid)
    for appid in new_data:
        if appid not in seen:
            data.append(appid)
            seen.add(appid)          
    
    # Se guardan los datos obtenidos
    write_to_file(data, appidlist_file)
    list_info = {"last_appid": data[-1], "size":len(data)}
    write_to_file(list_info, appidlist_info_file)
    

if __name__ == "__main__":
    A_lista_juegos()