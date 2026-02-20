from utils.config import appidlist_file
from utils.files import read_file, write_to_file, file_exists
from utils.steam_requests import get_appids
from utils.sesion import handle_input, tratar_existe_fichero, read_config, update_config

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
    
def _parametros_de_request():
    mensaje = """Elige modo de ejecución:\n\n1. Elegir manualmente el los parámetros\n2. Extraer nuevos juegos\n
Introduce elección: """

    respuesta = handle_input(mensaje, lambda x: x in {"1", "2"})
    n_appids = 0
    last_appid = 0
    
    if respuesta == "1": # Elegir manualmente el los parámetros
        mensaje = "Número de appids a extraer: "
        n_appids = int(handle_input(mensaje, lambda x: x.isdigit()))
        
        mensaje = "Appid desde el que hay que extraer: "
        last_appid = handle_input(mensaje, lambda x: x.isdigit())

    elif respuesta == "2": # Extraer nuevos juegos
        mensaje = "Número de appids nuevos a extraer: "
        n_appids = int(handle_input(mensaje, lambda x: x.isdigit()))
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
        minio (dic): diccionario de la forma {"minio_upload": False, "minio_download": False} para activar y desactivar subida y bajada de MinIO
    
    Returns:
        None
    """
    data = []
    seen = set()

    # Si existe lista anterior, ¿se quiere sobreescribir o seguir a partir del mismo?
    overwrite_file = False
    if file_exists(appidlist_file, minio):
        origen = " en MinIO" if minio["minio_download"] else ""
        mensaje = f"El fichero de lista de appids ya existe{origen}:\n\n1. Añadir contenido al fichero existente\n2. Sobreescribir fichero\n\nIntroduce elección: "
        overwrite_file = tratar_existe_fichero(mensaje)
        if not overwrite_file:
            old_data = read_file(appidlist_file, minio)
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
    write_to_file(data, appidlist_file, minio)
    list_info = {"last_appid": data[-1], "size":len(data)}
    update_config("A", list_info)
    

if __name__ == "__main__":
    A_lista_juegos()