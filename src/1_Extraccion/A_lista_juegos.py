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

from src.utils.config import appidlist_file
from src.utils.files import read_file, write_to_file, file_exists
from utils_extraccion.steam_requests import get_appids
from utils_extraccion.sesion import handle_input, ask_overwrite_file, read_config, update_config
    
def _get_request_params():
    message = """Elige modo de ejecución:\n\n1. Elegir manualmente el los parámetros\n2. Extraer nuevos juegos\n
Introduce elección: """

    response = handle_input(message, lambda x: x in {"1", "2"})
    n_appids = 0
    last_appid = 0
    
    if response == "1": # Elegir manualmente el los parámetros
        message = "Número de appids a extraer: "
        n_appids = int(handle_input(message, lambda x: x.isdigit()))
        
        message = "Appid desde el que hay que extraer: "
        last_appid = handle_input(message, lambda x: x.isdigit())

    elif response == "2": # Extraer nuevos juegos
        message = "Número de appids nuevos a extraer: "
        n_appids = int(handle_input(message, lambda x: x.isdigit()))
        info = read_config("A", {"last_appid" : 0, "size" : 0})
        if info is None:
            appid_list = read_file(appidlist_file)
            last_appid = appid_list[-1]
        else:
            last_appid = info.get("last_appid")

    return int(n_appids), str(last_appid)

def A_lista_juegos(minio):
    """
    Obtiene la lista completa de appids de los juegos de Steam

    Args:
        minio (dic): diccionario de la forma {"minio_write": False, "minio_read": False} para activar y desactivar subida y bajada de MinIO
    
    Returns:
        None
    """
    data = []
    seen = set()

    # Si existe lista anterior, ¿se quiere sobreescribir o seguir a partir del mismo?
    overwrite_file = False
    if file_exists(appidlist_file, minio):
        origin = " en MinIO" if minio["minio_read"] else ""
        message = f"El fichero de lista de appids ya existe{origin}:\n\n1. Añadir contenido al fichero existente\n2. Sobreescribir fichero\n\nIntroduce elección: "
        overwrite_file = ask_overwrite_file(message)
        if not overwrite_file:
            old_data = read_file(appidlist_file, minio)
            data.extend(old_data)
            seen = set(data)

    # Parámetros de request
    n_appids, last_appid = _get_request_params()

    new_data = get_appids(n_appids, last_appid)
    for appid in new_data:
        if appid not in seen:
            data.append(appid)
            seen.add(appid)          
    
    # Se guardan los datos obtenidos
    write_to_file(data, appidlist_file, minio)
    list_info = {"last_appid": data[-1], "size":len(data)}
    update_config("A", list_info)